from dataclasses import fields

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculators.carrying_capacity import PastureParameters, calculate_pasture_limit
from app.calculators.recommended_herd import (
    CategoryEquivalents,
    HerdParameters,
    RecommendedHerd,
    recommend_herd,
    replacement_rate_for_calculation,
)
from app.models import AnimalCategory
from app.schemas.carrying_capacity import (
    CalculationWarning,
    CarryingCapacityInput,
    CarryingCapacityResult,
    HerdQuantity,
    RecommendedHerdRead,
    WarningCode,
    WeanedCalves,
)
from app.services.herds import UnitNotFoundError, category_codes, check_herd_rules
from app.services.parameters import get_parameters
from app.services.production_units import get_user_unit, read_unit

MISSING_INDEX = CalculationWarning(
    code=WarningCode.MISSING_INDEX,
    message="Falta cargar algún índice de corrección: se calculó sin él.",
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
# Parámetros del rodeo que salen de la tabla parameter; los toros pueden
# venir del pedido.
HERD_PARAMETER_KEYS = [field.name for field in fields(HerdParameters)]
# Categorías que forman el rodeo recomendado, en el orden en que se muestran
HERD_CODES = ["cow", "bull", "calf", "heifer"]


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
    check_herd_rules(data, category_codes(session))
    unit = read_unit(session, unit_id)
    pasture = calculate_pasture_limit(
        rainfall_mm=data.rainfall_mm,
        usable_area_ha=unit["usable_area_ha"],
        range_condition=data.range_condition,
        early_weaning=data.early_weaning,
        supplemented=data.supplemented,
        parameters=read_pasture_parameters(session),
    )
    recommended, herd_warnings = recommended_herd(
        session, data, pasture.pasture_limit_cow_equivalents
    )
    warnings = [MISSING_INDEX] if pasture.missing_index else []
    return CarryingCapacityResult(
        area_ha=unit["area_ha"],
        usable_area_ha=unit["usable_area_ha"],
        carrying_capacity_ha_per_cow_equivalent=(
            pasture.carrying_capacity_ha_per_cow_equivalent
        ),
        pasture_limit_cow_equivalents=pasture.pasture_limit_cow_equivalents,
        recommended_herd=recommended,
        warnings=warnings + herd_warnings,
    )


def read_herd_parameters(
    session: Session, bulls_per_100_cows: float | None
) -> HerdParameters:
    """Parámetros del rodeo; los toros del pedido reemplazan al parámetro."""
    values = get_parameters(session, HERD_PARAMETER_KEYS)
    if bulls_per_100_cows is not None:
        values["bulls_per_100_cows"] = bulls_per_100_cows
    return TypeAdapter(HerdParameters).validate_python(values)


def herd_categories(session: Session) -> dict[str, AnimalCategory]:
    """Categorías del rodeo recomendado, por código."""
    rows = session.scalars(
        select(AnimalCategory).where(AnimalCategory.code.in_(HERD_CODES))
    )
    return {category.code: category for category in rows}


def recommended_herd(
    session: Session, data: CarryingCapacityInput, limit_cow_equivalents: float
) -> tuple[RecommendedHerdRead | None, list[CalculationWarning]]:
    """Rodeo recomendado y sus avisos.

    Sin vacas no se arma el rodeo. Las reglas del rodeo garantizan que, si hay
    vacas, vienen la reposición y el destete.
    """
    codes = category_codes(session)
    has_cows = any(
        codes[item.animal_category_id] == "cow" and item.quantity > 0
        for item in data.categories
    )
    if not has_cows:
        return None, []

    parameters = read_herd_parameters(session, data.bulls_per_100_cows)
    categories = herd_categories(session)
    warnings = []
    _, exceeds = replacement_rate_for_calculation(
        data.replacement_rate, data.weaning_rate, parameters.weaned_calf_female_share
    )
    if exceeds:
        warnings.append(REPLACEMENT_EXCEEDS_FEMALES)

    herd = recommend_herd(
        limit_cow_equivalents=limit_cow_equivalents,
        replacement_rate=data.replacement_rate,
        weaning_rate=data.weaning_rate,
        early_weaning=data.early_weaning,
        parameters=parameters,
        equivalents=CategoryEquivalents(
            **{code: categories[code].cow_equivalent for code in HERD_CODES}
        ),
    )
    if herd is None:
        return None, [*warnings, HERD_DOES_NOT_FIT]
    return recommended_read(herd, categories), warnings


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
        categories=[
            HerdQuantity(
                animal_category_id=categories[code].id,
                name=categories[code].name,
                quantity=quantities[code],
            )
            for code in HERD_CODES
        ],
        weaned_calves=WeanedCalves(
            males=herd.weaned_males, females=herd.weaned_females
        ),
    )
