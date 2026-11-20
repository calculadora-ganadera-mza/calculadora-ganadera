from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import LimitedBy
from app.schemas.herd import HerdData


class CarryingCapacityInput(HerdData):
    """Datos del rodeo más la lluvia de la campaña anterior."""

    rainfall_mm: float = Field(gt=0, allow_inf_nan=False)
    # Si se omite, se usa el parámetro bulls_per_100_cows
    bulls_per_100_cows: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class WarningCode(StrEnum):
    MISSING_INDEX = "missing_index"
    PARTIAL_WATER_DATA = "partial_water_data"
    WATER_NOT_EVALUATED = "water_not_evaluated"
    REPLACEMENT_EXCEEDS_FEMALES = "replacement_exceeds_females"
    HERD_DOES_NOT_FIT = "herd_does_not_fit"


class CalculationWarning(BaseModel):
    code: WarningCode
    message: str


class HerdQuantity(BaseModel):
    animal_category_id: int
    name: str
    quantity: float


class WeanedCalves(BaseModel):
    males: int
    females: int


class RecommendedHerdRead(BaseModel):
    """Rodeo recomendado, en cantidades enteras."""

    cow_equivalents: float
    categories: list[HerdQuantity]
    weaned_calves: WeanedCalves


class CarryingCapacityResult(BaseModel):
    """Resultado del cálculo.

    El contrato pide además scaled_herd y load_thermometer: se agregan en las
     issues que los calculan (#16 y #17).
    """

    area_ha: float
    usable_area_ha: float
    carrying_capacity_ha_per_cow_equivalent: float
    pasture_limit_cow_equivalents: float
    water: WaterRead
    max_herd: MaxHerdRead
    # None si no hay vacas o si no entra ni una vaca con su toro
    recommended_herd: RecommendedHerdRead | None
    warnings: list[CalculationWarning]


class WaterRead(BaseModel):
    """Límite por agua.
    El contrato pide además summer_need_l_day y winter_need_l_day: se agregan
    en la issue #17.
    """

    evaluated: bool
    # None si no se evaluó
    limit_cow_equivalents: float | None
    # None si ninguna aguada que cuenta para el sector tiene litros cargados
    refill_l_day: float | None


class MaxHerdRead(BaseModel):
    """Rodeo máximo, sin redondear."""

    cow_equivalents: float
    limited_by: LimitedBy
    # Vacío si no hay vacas
    categories: list[HerdQuantity]
