from dataclasses import fields

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.calculators.carrying_capacity import PastureParameters, calculate_pasture_limit
from app.schemas.carrying_capacity import (
    CalculationWarning,
    CarryingCapacityInput,
    CarryingCapacityResult,
    WarningCode,
)
from app.services.herds import UnitNotFoundError, category_codes, check_herd_rules
from app.services.parameters import get_parameters
from app.services.production_units import get_user_unit, read_unit

MISSING_INDEX = CalculationWarning(
    code=WarningCode.MISSING_INDEX,
    message="Falta cargar algún índice de corrección: se calculó sin él.",
)

PASTURE_PARAMETERS = TypeAdapter(PastureParameters)


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
    return CarryingCapacityResult(
        area_ha=unit["area_ha"],
        usable_area_ha=unit["usable_area_ha"],
        carrying_capacity_ha_per_cow_equivalent=(
            pasture.carrying_capacity_ha_per_cow_equivalent
        ),
        pasture_limit_cow_equivalents=pasture.pasture_limit_cow_equivalents,
        warnings=[MISSING_INDEX] if pasture.missing_index else [],
    )
