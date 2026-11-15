from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.herd import HerdData


class CarryingCapacityInput(HerdData):
    """Datos del rodeo más la lluvia de la campaña anterior."""

    rainfall_mm: float = Field(gt=0, allow_inf_nan=False)


class WarningCode(StrEnum):
    MISSING_INDEX = "missing_index"


class CalculationWarning(BaseModel):
    code: WarningCode
    message: str


class CarryingCapacityResult(BaseModel):
    """Resultado del cálculo.

    El contrato pide además water, max_herd, recommended_herd, scaled_herd y
    load_thermometer: se agregan en las issues que los calculan (#14 a #17).
    """

    area_ha: float
    usable_area_ha: float
    carrying_capacity_ha_per_cow_equivalent: float
    pasture_limit_cow_equivalents: float
    warnings: list[CalculationWarning]
