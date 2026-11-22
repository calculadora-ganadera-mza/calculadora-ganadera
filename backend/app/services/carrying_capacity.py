from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from typing import Annotated

from pydantic import Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculators.carrying_capacity import PastureParameters, calculate_pasture_limit
from app.calculators.current_herd import (
    ScaledHerd,
    current_herd_max,
    herd_total,
    herd_with_calves,
    load_status,
    scale_herd,
)
from app.calculators.recommended_herd import (
    CategoryEquivalents,
    HerdParameters,
    RecommendedHerd,
    annual_equivalents,
    cow_equivalents_per_cow,
    recommend_herd,
    replacement_rate_for_calculation,
    spread_cow_equivalents,
)
from app.calculators.water import (
    CategoryWater,
    WaterParameters,
    herd_calendar,
    herd_litres,
    litres_per_cow,
    max_herd,
    months_between,
    season_litres,
    water_limit,
)
from app.models import AnimalCategory
from app.models.enums import LimitedBy
from app.schemas.carrying_capacity import (
    CalculationWarning,
    CarryingCapacityInput,
    CarryingCapacityResult,
    HerdQuantity,
    LoadThermometerRead,
    MaxHerdRead,
    RecommendedHerdRead,
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

WATER_WITHOUT_COWS = CalculationWarning(
    code=WarningCode.WATER_NOT_EVALUATED,
    message="Sin vacas no se arma la composición del rodeo: no se evaluó el agua.",
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
# Categorías que forman el rodeo recomendado, en el orden en que se muestran
HERD_CODES = ["cow", "bull", "calf", "heifer"]


@dataclass(frozen=True)
class HerdResults:
    """Lo que depende del rodeo.

    El agua, el rodeo máximo, el rodeo recomendado y Mi rodeo ajustado.
    """

    water: WaterRead
    max_herd: MaxHerdRead
    recommended_herd: RecommendedHerdRead | None
    scaled_herd: ScaledHerdRead | None
    current_cow_equivalents: float
    current_herd_max: float
    warnings: list[CalculationWarning]


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
    if loaded.get("cow", 0) > 0:
        herd = herd_results(session, data, loaded, categories, pasture_limit, water)
    else:
        equivalents = {
            code: category.cow_equivalent for code, category in categories.items()
        }
        herd = results_without_cows(
            pasture_limit, water, herd_total(loaded, equivalents)
        )
    below = herd.current_herd_max * read_load_threshold(session)
    warnings = [MISSING_INDEX] if pasture.missing_index else []
    return CarryingCapacityResult(
        area_ha=unit["area_ha"],
        usable_area_ha=unit["usable_area_ha"],
        carrying_capacity_ha_per_cow_equivalent=(
            pasture.carrying_capacity_ha_per_cow_equivalent
        ),
        pasture_limit_cow_equivalents=pasture_limit,
        water=herd.water,
        max_herd=herd.max_herd,
        recommended_herd=herd.recommended_herd,
        scaled_herd=herd.scaled_herd,
        load_thermometer=LoadThermometerRead(
            status=load_status(
                herd.current_cow_equivalents, herd.current_herd_max, below
            ),
            current_cow_equivalents=herd.current_cow_equivalents,
            max_cow_equivalents=herd.current_herd_max,
            below_cow_equivalents=below,
        ),
        warnings=warnings + herd.warnings,
    )


def results_without_cows(
    pasture_limit: float, water: AvailableWater, current_cow_equivalents: float
) -> HerdResults:
    """Sin vacas no hay composición: el agua no se evalúa y el rodeo máximo es
    el límite por pasto."""
    return HerdResults(
        water=WaterRead(
            evaluated=False,
            limit_cow_equivalents=None,
            refill_l_day=water.refill_l_day,
            summer_need_l_day=None,
            winter_need_l_day=None,
        ),
        max_herd=MaxHerdRead(
            cow_equivalents=pasture_limit,
            limited_by=LimitedBy.PASTURE,
            categories=[],
        ),
        recommended_herd=None,
        scaled_herd=None,
        current_cow_equivalents=current_cow_equivalents,
        current_herd_max=pasture_limit,
        warnings=[WATER_WITHOUT_COWS],
    )


def herd_results(
    session: Session,
    data: CarryingCapacityInput,
    loaded: dict[str, int],
    categories: dict[str, AnimalCategory],
    pasture_limit: float,
    water: AvailableWater,
) -> HerdResults:
    """Límite por agua, rodeo máximo, rodeo recomendado y Mi rodeo ajustado de
    un rodeo de vacas.

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
    equivalents = CategoryEquivalents(
        **{code: categories[code].cow_equivalent for code in HERD_CODES}
    )
    rate, exceeds = replacement_rate_for_calculation(
        data.replacement_rate, data.weaning_rate, parameters.weaned_calf_female_share
    )
    warnings = [REPLACEMENT_EXCEEDS_FEMALES] if exceeds else []

    summer, winter = seasonal_litres(
        session, data.breeding_start, data.early_weaning, parameters, categories
    )
    composition_ev = cow_equivalents_per_cow(
        rate, data.early_weaning, parameters, equivalents
    )
    summer_l_day = litres_per_cow(summer, rate, parameters)
    winter_l_day = litres_per_cow(winter, rate, parameters)
    pasture_cows = pasture_limit / composition_ev
    refill = water.refill_l_day
    limit = None
    if refill is None:
        warnings.append(WATER_WITHOUT_LITRES)
    else:
        if water.partial:
            warnings.append(PARTIAL_WATER_DATA)
        limit = water_limit(
            available_l_day=refill,
            composition_l_day=summer_l_day,
            composition_cow_equivalents=composition_ev,
        )
    max_cow_equivalents, limited_by = max_herd(pasture_limit, limit)

    herd = recommend_herd(
        limit_cow_equivalents=max_cow_equivalents,
        replacement_rate=data.replacement_rate,
        weaning_rate=data.weaning_rate,
        early_weaning=data.early_weaning,
        parameters=parameters,
        equivalents=equivalents,
        # Con litros cargados, el rodeo entero tampoco puede pasarse del agua
        # de verano.
        fits=(
            None
            if refill is None
            else lambda candidate: herd_litres(candidate, summer) <= refill
        ),
    )
    if herd is None:
        warnings.append(HERD_DOES_NOT_FIT)
    spread = spread_cow_equivalents(
        max_cow_equivalents, rate, data.early_weaning, parameters, equivalents
    )

    calf_ev, _ = annual_equivalents(data.early_weaning, parameters, equivalents)
    equivalents_per_head, litres_per_head = per_head_values(
        categories, calf_ev, summer.calf
    )
    current = herd_with_calves(
        loaded,
        replacement_rate=data.replacement_rate,
        weaning_rate=data.weaning_rate,
        parameters=parameters,
    )
    current_max = current_herd_max(
        max_cow_equivalents=max_cow_equivalents,
        available_l_day=refill,
        herd=current,
        summer_l_day=litres_per_head,
        cow_equivalents=equivalents_per_head,
    )
    scaled = scale_herd(
        loaded=loaded,
        limit_cow_equivalents=current_max,
        replacement_rate=data.replacement_rate,
        weaning_rate=data.weaning_rate,
        parameters=parameters,
        cow_equivalents=equivalents_per_head,
        # Al redondear, Mi rodeo ajustado tampoco puede pasarse del agua de
        # verano.
        fits=(
            None
            if refill is None
            else lambda candidate: herd_total(candidate, litres_per_head) <= refill
        ),
    )
    return HerdResults(
        water=WaterRead(
            evaluated=limit is not None,
            limit_cow_equivalents=limit,
            refill_l_day=refill,
            summer_need_l_day=pasture_cows * summer_l_day,
            winter_need_l_day=pasture_cows * winter_l_day,
        ),
        max_herd=MaxHerdRead(
            cow_equivalents=max_cow_equivalents,
            limited_by=limited_by,
            categories=herd_quantities(spread, categories),
        ),
        recommended_herd=None if herd is None else recommended_read(herd, categories),
        scaled_herd=(
            None
            if scaled is None
            else scaled_read(scaled, current, current_max, categories)
        ),
        current_cow_equivalents=herd_total(current, equivalents_per_head),
        current_herd_max=current_max,
        warnings=warnings,
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


def recommended_read(
    herd: RecommendedHerd, categories: dict[str, AnimalCategory]
) -> RecommendedHerdRead:
    """El rodeo recomendado en el formato de la API."""
    quantities = {
        "cow": herd.cows,
        "bull": herd.bulls,
        "calf": herd.replacement_calves,
        "heifer": herd.heifers,
    }
    return RecommendedHerdRead(
        cow_equivalents=herd.cow_equivalents,
        categories=herd_quantities(quantities, categories),
        weaned_calves=WeanedCalves(
            males=herd.weaned_males, females=herd.weaned_females
        ),
    )


def per_head_values(
    categories: dict[str, AnimalCategory], calf_ev: float, calf_l_day: float
) -> tuple[dict[str, float], dict[str, float]]:
    """EV y litros de verano por cabeza, por código de categoría.

    Los animales cargados van con los valores de su categoría; las terneras de
    reposición, con su EV anual y sus litros según el calendario.
    """
    equivalents = {
        code: category.cow_equivalent for code, category in categories.items()
    }
    litres = {
        code: category.summer_water_l_day for code, category in categories.items()
    }
    return equivalents | {"calf": calf_ev}, litres | {"calf": calf_l_day}


def scaled_read(
    scaled: ScaledHerd,
    current: Mapping[str, int],
    max_cow_equivalents: float,
    categories: dict[str, AnimalCategory],
) -> ScaledHerdRead:
    """Mi rodeo ajustado en el formato de la API, junto al rodeo actual."""
    return ScaledHerdRead(
        cow_equivalents=scaled.cow_equivalents,
        max_cow_equivalents=max_cow_equivalents,
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
