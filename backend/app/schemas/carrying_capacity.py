from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from app.models.enums import CalculationKind, CorrectionIndexCode, LimitedBy, LoadStatus
from app.schemas.animal_category import AnimalCategoryRead
from app.schemas.herd import HerdData


class CarryingCapacityInput(HerdData):
    """Datos del rodeo más la lluvia de la campaña anterior."""

    rainfall_mm: float = Field(gt=0, allow_inf_nan=False)
    # Si se omite, se usa el parámetro bulls_per_100_cows
    bulls_per_100_cows: float | None = Field(default=None, gt=0, allow_inf_nan=False)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # En el contrato, bulls_per_100_cows se omite cuando no se informó
        data = handler(self)
        if data.get("bulls_per_100_cows") is None:
            data.pop("bulls_per_100_cows", None)
        return data


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


class MaxBreedingHerdRead(BaseModel):
    """Rodeo de cría máximo, en cantidades enteras."""

    cow_equivalents: float
    categories: list[HerdQuantity]
    weaned_calves: WeanedCalves


class ScaledHerdQuantity(BaseModel):
    animal_category_id: int
    name: str
    # Cabezas del rodeo actual y de Mi rodeo ajustado al campo
    current_quantity: int
    quantity: int


class ScaledHerdRead(BaseModel):
    """Mi rodeo ajustado al campo, en cantidades enteras."""

    cow_equivalents: float
    categories: list[ScaledHerdQuantity]


class LoadThermometerRead(BaseModel):
    status: LoadStatus
    current_cow_equivalents: float
    below_cow_equivalents: float


class CorrectionIndexRead(BaseModel):
    code: CorrectionIndexCode
    applies: bool
    # None si el índice todavía no se cargó
    value: float | None


class PastureBreakdownRead(BaseModel):
    """Pasos del cálculo de la receptividad."""

    cow_equivalent_dm_intake_kg_year: float
    consumable_forage_kg_ha_year: float
    base_carrying_capacity_ha_per_cow_equivalent: float
    # Estado del campo, destete precoz y suplementación, en ese orden
    indices: list[CorrectionIndexRead]


class CarryingCapacityResult(BaseModel):
    """Resultado del cálculo."""

    area_ha: float
    usable_area_ha: float
    carrying_capacity_ha_per_cow_equivalent: float
    pasture_limit_cow_equivalents: float
    pasture_breakdown: PastureBreakdownRead
    water: WaterRead
    max_herd: MaxHerdRead
    # None si no hay vacas o si no entra ni una vaca con su toro
    max_breeding_herd: MaxBreedingHerdRead | None
    # None si no hay vacas o si no entra ni una vaca con su parte de los demás
    # animales
    scaled_herd: ScaledHerdRead | None
    load_thermometer: LoadThermometerRead
    warnings: list[CalculationWarning]


class WaterRead(BaseModel):
    """Límite por agua y demanda del rodeo que permite el pasto."""

    evaluated: bool
    # None si no se evaluó
    limit_cow_equivalents: float | None
    # None si ninguna aguada que cuenta para el sector tiene litros cargados
    refill_l_day: float | None
    # None si no hay animales cargados
    summer_need_l_day: float | None
    winter_need_l_day: float | None


class MaxHerdRead(BaseModel):
    """Rodeo máximo, sin redondear."""

    cow_equivalents: float
    limited_by: LimitedBy


class CarryingCapacityCalculationCreate(BaseModel):
    """Pedido para guardar un resultado de la campaña o una simulación."""

    season_id: int
    kind: CalculationKind
    update_season: bool = False
    input: CarryingCapacityInput


class ReferenceValuesRead(BaseModel):
    """Valores de referencia con los que se hizo el cálculo."""

    parameters: dict[str, float | None]
    animal_categories: list[AnimalCategoryRead]


class CarryingCapacityCalculationSummaryRead(BaseModel):
    """Resumen liviano de un cálculo guardado para el historial."""

    id: int
    production_unit_id: int
    season_id: int
    scenario_name: str
    production_unit_name: str
    season_start_date: date
    season_end_date: date
    kind: CalculationKind
    created_at: datetime
    rainfall_mm: float
    carrying_capacity_ha_per_cow_equivalent: float
    max_herd_cow_equivalents: float


class CarryingCapacityCalculationRead(BaseModel):
    """Cálculo guardado, con sus datos, valores de referencia y resultado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    production_unit_id: int
    season_id: int
    scenario_name: str
    production_unit_name: str
    season_start_date: date
    season_end_date: date
    kind: CalculationKind
    created_at: datetime
    season_updated: bool
    input: CarryingCapacityInput
    reference_values: ReferenceValuesRead
    result: CarryingCapacityResult
