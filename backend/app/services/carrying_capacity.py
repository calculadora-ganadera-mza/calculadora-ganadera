from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from typing import Annotated

from pydantic import Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculators.carrying_capacity import PastureParameters, calculate_pasture_limit
from app.calculators.current_herd import (
    CALF,
    COW,
    ScaledHerd,
    herd_total,
    herd_with_calves,
    load_status,
    scale_herd,
)
from app.calculators.max_breeding_herd import (
    CategoryEquivalents,
    HerdParameters,
    MaxBreedingHerd,
    annual_equivalents,
    calculate_max_breeding_herd,
    replacement_rate_for_calculation,
)
from app.calculators.water import (
    CategoryWater,
    WaterParameters,
    herd_calendar,
    herd_litres,
    max_herd,
    months_between,
    season_litres,
    water_limit,
    water_need,
)
from app.models import AnimalCategory
from app.schemas.carrying_capacity import (
    CalculationWarning,
    CarryingCapacityInput,
    CarryingCapacityResult,
    HerdQuantity,
    LoadThermometerRead,
    MaxBreedingHerdRead,
    MaxHerdRead,
    ScaledHerdQuantity,
    ScaledHerdRead,
    WarningCode,
    WaterRead,
    WeanedCalves,
)
from app.services.herds import UnitNotFoundError, check_herd_rules
from app.services.parameters import get_parameters
from app.services.production_units import get_user_unit, read_unit
from app.services.water_points import AvailableWater, available_water

MISSING_INDEX = CalculationWarning(
    code=WarningCode.MISSING_INDEX,
    message="Falta cargar algún índice de corrección: se calculó sin él.",
)

PARTIAL_WATER_DATA = CalculationWarning(
    code=WarningCode.PARTIAL_WATER_DATA,
    message=(
        "Algunas aguadas no tienen litros cargados: el agua se calculó solo "
        "con las que los tienen."
    ),
)

WATER_WITHOUT_LITRES = CalculationWarning(
    code=WarningCode.WATER_NOT_EVALUATED,
    message="Ninguna aguada tiene litros cargados: no se evaluó el agua.",
)

WATER_WITHOUT_ANIMALS = CalculationWarning(
    code=WarningCode.WATER_NOT_EVALUATED,
    message="No hay animales cargados: no se evaluó el agua.",
)

REPLACEMENT_EXCEEDS_FEMALES = CalculationWarning(
    code=WarningCode.REPLACEMENT_EXCEEDS_FEMALES,
    message=(
        "La reposición pide más terneras que las hembras destetadas: "
        "se contaron todas las hembras."
    ),
)
HERD_DOES_NOT_FIT = CalculationWarning(
    code=WarningCode.HERD_DOES_NOT_FIT,
    message="El campo no alcanza para una vaca con su toro.",
)

PASTURE_PARAMETERS = TypeAdapter(PastureParameters)
WATER_PARAMETERS = TypeAdapter(WaterParameters)
HERD_PARAMETERS = TypeAdapter(HerdParameters)
LOAD_THRESHOLD = TypeAdapter(Annotated[float, Field(gt=0, le=1)])
LOAD_THRESHOLD_KEY = "load_thermometer_below_threshold"
# Parámetros del rodeo que salen de la tabla parameter; los toros pueden
# venir del pedido.
HERD_PARAMETER_KEYS = [field.name for field in fields(HerdParameters)]
WATER_PARAMETER_KEYS = [field.name for field in fields(WaterParameters)]
# Categorías del rodeo de cría máximo, en el orden en que se muestran
HERD_CODES = ["cow", "bull", "calf", "heifer"]


@dataclass(frozen=True)
class CowHerd:
    """Datos de un rodeo con vacas para sumar las terneras de reposición y armar
    el rodeo de cría máximo y Mi rodeo ajustado al campo."""

    replacement_rate: float
    weaning_rate: float
    early_weaning: bool
    parameters: HerdParameters
    equivalents: CategoryEquivalents
    # Litros por cabeza de cada estación, según el calendario del rodeo
    summer: CategoryWater
    winter: CategoryWater


@dataclass(frozen=True)
class PerHead:
    """EV y litros por día de verano y de invierno por cabeza, por código de
    categoría."""

    cow_equivalents: dict[str, float]
    summer_l_day: dict[str, float]
    winter_l_day: dict[str, float]


def read_pasture_parameters(session: Session) -> PastureParameters:
    """Parámetros del cálculo por pasto, leídos de la tabla parameter.

    Falla si un parámetro que no es índice está sin valor.
    """
    keys = [field.name for field in fields(PastureParameters)]
    return PASTURE_PARAMETERS.validate_python(get_parameters(session, keys))


def calculate(
    session: Session, user_id: int, unit_id: int, data: CarryingCapacityInput
) -> CarryingCapacityResult:
    """Calcula con los datos recibidos y la superficie del sector, sin guardar."""
    if get_user_unit(session, user_id, unit_id) is None:
        raise UnitNotFoundError("Sector no encontrado.")
    categories = herd_categories(session)
    codes = {category.id: code for code, category in categories.items()}
    check_herd_rules(data, codes)
    unit = read_unit(session, unit_id)
    pasture = calculate_pasture_limit(
        rainfall_mm=data.rainfall_mm,
        usable_area_ha=unit["usable_area_ha"],
        range_condition=data.range_condition,
        early_weaning=data.early_weaning,
        supplemented=data.supplemented,
        parameters=read_pasture_parameters(session),
    )
    pasture_limit = pasture.pasture_limit_cow_equivalents
    water = available_water(session, unit_id)
    loaded = {codes[item.animal_category_id]: item.quantity for item in data.categories}
    warnings = [MISSING_INDEX] if pasture.missing_index else []

    cow_herd = (
        read_cow_herd(session, data, categories) if loaded.get(COW, 0) > 0 else None
    )
    per_head = per_head_values(categories, cow_herd)
    current = current_herd(loaded, cow_herd)
    current_cow_equivalents = herd_total(current, per_head.cow_equivalents)
    water_read, water_warnings = water_results(
        water,
        pasture_limit=pasture_limit,
        current_cow_equivalents=current_cow_equivalents,
        summer_l_day=herd_total(current, per_head.summer_l_day),
        winter_l_day=herd_total(current, per_head.winter_l_day),
    )
    warnings += water_warnings
    max_cow_equivalents, limited_by = max_herd(
        pasture_limit, water_read.limit_cow_equivalents
    )

    max_breeding_herd = scaled_herd = None
    if cow_herd is not None:
        max_breeding_herd, scaled_herd, herd_warnings = cow_herd_results(
            cow_herd,
            loaded=loaded,
            current=current,
            per_head=per_head,
            pasture_limit=pasture_limit,
            max_cow_equivalents=max_cow_equivalents,
            refill_l_day=water.refill_l_day,
            categories=categories,
        )
        warnings += herd_warnings

    below = max_cow_equivalents * read_load_threshold(session)
    return CarryingCapacityResult(
        area_ha=unit["area_ha"],
        usable_area_ha=unit["usable_area_ha"],
        carrying_capacity_ha_per_cow_equivalent=(
            pasture.carrying_capacity_ha_per_cow_equivalent
        ),
        pasture_limit_cow_equivalents=pasture_limit,
        water=water_read,
        max_herd=MaxHerdRead(
            cow_equivalents=max_cow_equivalents, limited_by=limited_by
        ),
        max_breeding_herd=max_breeding_herd,
        scaled_herd=scaled_herd,
        load_thermometer=LoadThermometerRead(
            status=load_status(current_cow_equivalents, max_cow_equivalents, below),
            current_cow_equivalents=current_cow_equivalents,
            below_cow_equivalents=below,
        ),
        warnings=warnings,
    )


def read_cow_herd(
    session: Session,
    data: CarryingCapacityInput,
    categories: dict[str, AnimalCategory],
) -> CowHerd:
    """Datos de un rodeo con vacas.

    Las reglas del rodeo garantizan que, si hay vacas, vienen la reposición,
    el destete y el inicio del entore.
    """
    if (
        data.replacement_rate is None
        or data.weaning_rate is None
        or data.breeding_start is None
    ):
        # check_herd_rules lo impide: llegar acá es un error de programación
        raise RuntimeError("Rodeo con vacas sin reposición, destete o entore.")
    parameters = read_herd_parameters(session, data.bulls_per_100_cows)
    summer, winter = seasonal_litres(
        session, data.breeding_start, data.early_weaning, parameters, categories
    )
    return CowHerd(
        replacement_rate=data.replacement_rate,
        weaning_rate=data.weaning_rate,
        early_weaning=data.early_weaning,
        parameters=parameters,
        equivalents=CategoryEquivalents(
            **{code: categories[code].cow_equivalent for code in HERD_CODES}
        ),
        summer=summer,
        winter=winter,
    )


def per_head_values(
    categories: dict[str, AnimalCategory], cow_herd: CowHerd | None
) -> PerHead:
    """EV y litros por cabeza de cada categoría.

    Los animales cargados van con los valores de su categoría. Con vacas, las
    terneras de reposición van con su EV anual y con los litros de cada
    estación según el calendario.
    """
    per_head = PerHead(
        cow_equivalents={
            code: category.cow_equivalent for code, category in categories.items()
        },
        summer_l_day={
            code: category.summer_water_l_day for code, category in categories.items()
        },
        winter_l_day={
            code: category.winter_water_l_day for code, category in categories.items()
        },
    )
    if cow_herd is None:
        return per_head
    calf_ev, _ = annual_equivalents(
        cow_herd.early_weaning, cow_herd.parameters, cow_herd.equivalents
    )
    return PerHead(
        cow_equivalents=per_head.cow_equivalents | {CALF: calf_ev},
        summer_l_day=per_head.summer_l_day | {CALF: cow_herd.summer.calf},
        winter_l_day=per_head.winter_l_day | {CALF: cow_herd.winter.calf},
    )


def current_herd(loaded: dict[str, int], cow_herd: CowHerd | None) -> dict[str, int]:
    """Rodeo actual: los animales cargados y, si hay vacas, sus terneras de
    reposición."""
    if cow_herd is None:
        return loaded
    return herd_with_calves(
        loaded,
        replacement_rate=cow_herd.replacement_rate,
        weaning_rate=cow_herd.weaning_rate,
        parameters=cow_herd.parameters,
    )


def water_results(
    water: AvailableWater,
    *,
    pasture_limit: float,
    current_cow_equivalents: float,
    summer_l_day: float,
    winter_l_day: float,
) -> tuple[WaterRead, list[CalculationWarning]]:
    """Límite por agua y demanda, con los litros por EV del rodeo actual.

    summer_l_day y winter_l_day son los litros por día del rodeo actual. Sin
    animales cargados no hay litros por EV: el agua no se evalúa.
    """
    refill = water.refill_l_day
    # Sin animales, o con todas las cantidades en 0, los EV suman 0 exacto
    if current_cow_equivalents == 0:
        not_evaluated = WaterRead(
            evaluated=False,
            limit_cow_equivalents=None,
            refill_l_day=refill,
            summer_need_l_day=None,
            winter_need_l_day=None,
        )
        return not_evaluated, [WATER_WITHOUT_ANIMALS]
    limit = None
    if refill is None:
        warnings = [WATER_WITHOUT_LITRES]
    else:
        warnings = [PARTIAL_WATER_DATA] if water.partial else []
        limit = water_limit(
            available_l_day=refill,
            herd_l_day=summer_l_day,
            herd_cow_equivalents=current_cow_equivalents,
        )
    evaluated = WaterRead(
        evaluated=limit is not None,
        limit_cow_equivalents=limit,
        refill_l_day=refill,
        summer_need_l_day=water_need(
            limit_cow_equivalents=pasture_limit,
            herd_l_day=summer_l_day,
            herd_cow_equivalents=current_cow_equivalents,
        ),
        winter_need_l_day=water_need(
            limit_cow_equivalents=pasture_limit,
            herd_l_day=winter_l_day,
            herd_cow_equivalents=current_cow_equivalents,
        ),
    )
    return evaluated, warnings


def cow_herd_results(
    herd: CowHerd,
    *,
    loaded: Mapping[str, int],
    current: Mapping[str, int],
    per_head: PerHead,
    pasture_limit: float,
    max_cow_equivalents: float,
    refill_l_day: float | None,
    categories: dict[str, AnimalCategory],
) -> tuple[MaxBreedingHerdRead | None, ScaledHerdRead | None, list[CalculationWarning]]:
    """Rodeo de cría máximo y Mi rodeo ajustado al campo de un rodeo con vacas.

    El rodeo de cría parte del límite por pasto y Mi rodeo ajustado, del rodeo
    máximo. Con litros cargados, ninguno de los dos puede pasarse del agua de
    verano.
    """
    _, exceeds = replacement_rate_for_calculation(
        herd.replacement_rate,
        herd.weaning_rate,
        herd.parameters.weaned_calf_female_share,
    )
    warnings = [REPLACEMENT_EXCEEDS_FEMALES] if exceeds else []
    breeding = calculate_max_breeding_herd(
        limit_cow_equivalents=pasture_limit,
        replacement_rate=herd.replacement_rate,
        weaning_rate=herd.weaning_rate,
        early_weaning=herd.early_weaning,
        parameters=herd.parameters,
        equivalents=herd.equivalents,
        fits=(
            None
            if refill_l_day is None
            else lambda candidate: herd_litres(candidate, herd.summer) <= refill_l_day
        ),
    )
    if breeding is None:
        warnings.append(HERD_DOES_NOT_FIT)
    scaled = scale_herd(
        loaded=loaded,
        limit_cow_equivalents=max_cow_equivalents,
        replacement_rate=herd.replacement_rate,
        weaning_rate=herd.weaning_rate,
        parameters=herd.parameters,
        cow_equivalents=per_head.cow_equivalents,
        fits=(
            None
            if refill_l_day is None
            else lambda candidate: (
                herd_total(candidate, per_head.summer_l_day) <= refill_l_day
            )
        ),
    )
    return (
        None if breeding is None else max_breeding_read(breeding, categories),
        None if scaled is None else scaled_read(scaled, current, categories),
        warnings,
    )


def seasonal_litres(
    session: Session,
    breeding_start: date,
    early_weaning: bool,
    parameters: HerdParameters,
    categories: dict[str, AnimalCategory],
) -> tuple[CategoryWater, CategoryWater]:
    """Litros por cabeza en verano e invierno, según el calendario del rodeo."""
    water = read_water_parameters(session)
    calendar = herd_calendar(breeding_start, early_weaning, parameters, water)
    summer = months_between(water.summer_start_month, water.summer_end_month)
    winter = months_between(water.winter_start_month, water.winter_end_month)
    return (
        season_litres(
            CategoryWater(
                **{code: categories[code].summer_water_l_day for code in HERD_CODES}
            ),
            calendar,
            summer,
        ),
        season_litres(
            CategoryWater(
                **{code: categories[code].winter_water_l_day for code in HERD_CODES}
            ),
            calendar,
            winter,
        ),
    )


def read_herd_parameters(
    session: Session, bulls_per_100_cows: float | None
) -> HerdParameters:
    """Parámetros del rodeo; los toros del pedido reemplazan al parámetro."""
    values = get_parameters(session, HERD_PARAMETER_KEYS)
    if bulls_per_100_cows is not None:
        values["bulls_per_100_cows"] = bulls_per_100_cows
    return HERD_PARAMETERS.validate_python(values)


def read_water_parameters(session: Session) -> WaterParameters:
    """Parámetros del calendario del agua, leídos de la tabla parameter."""
    return WATER_PARAMETERS.validate_python(
        get_parameters(session, WATER_PARAMETER_KEYS)
    )


def read_load_threshold(session: Session) -> float:
    values = get_parameters(session, [LOAD_THRESHOLD_KEY])
    return LOAD_THRESHOLD.validate_python(values[LOAD_THRESHOLD_KEY])


def check_calculation_parameters(session: Session) -> None:
    """Revisa que los parámetros de la tabla cumplan los tipos del motor.

    Usa las mismas reglas que el cálculo (por ejemplo, meses de 1 a 12 y días
    enteros), para que un valor que lo rompería se rechace al guardarlo.
    Lanza ValidationError si alguno no las cumple.
    """
    read_pasture_parameters(session)
    read_water_parameters(session)
    read_herd_parameters(session, None)
    read_load_threshold(session)


def herd_categories(session: Session) -> dict[str, AnimalCategory]:
    """Todas las categorías de animales por código, en el orden de la tabla."""
    rows = session.scalars(select(AnimalCategory).order_by(AnimalCategory.id))
    return {category.code: category for category in rows}


def herd_quantities(
    quantities: Mapping[str, float], categories: dict[str, AnimalCategory]
) -> list[HerdQuantity]:
    """Cabezas por código de categoría, en el formato y el orden de la API."""
    return [
        HerdQuantity(
            animal_category_id=categories[code].id,
            name=categories[code].name,
            quantity=quantities[code],
        )
        for code in HERD_CODES
    ]


def max_breeding_read(
    herd: MaxBreedingHerd, categories: dict[str, AnimalCategory]
) -> MaxBreedingHerdRead:
    """El rodeo de cría máximo en el formato de la API."""
    quantities = {
        "cow": herd.cows,
        "bull": herd.bulls,
        "calf": herd.replacement_calves,
        "heifer": herd.heifers,
    }
    return MaxBreedingHerdRead(
        cow_equivalents=herd.cow_equivalents,
        categories=herd_quantities(quantities, categories),
        weaned_calves=WeanedCalves(
            males=herd.weaned_males, females=herd.weaned_females
        ),
    )


def scaled_read(
    scaled: ScaledHerd,
    current: Mapping[str, int],
    categories: dict[str, AnimalCategory],
) -> ScaledHerdRead:
    """Mi rodeo ajustado al campo en el formato de la API, junto al rodeo actual."""
    return ScaledHerdRead(
        cow_equivalents=scaled.cow_equivalents,
        categories=[
            ScaledHerdQuantity(
                animal_category_id=category.id,
                name=category.name,
                current_quantity=current[code],
                quantity=scaled.quantities[code],
            )
            for code, category in categories.items()
            if code in current
        ],
    )
