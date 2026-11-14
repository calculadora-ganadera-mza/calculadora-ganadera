from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.enums import RangeCondition

# Porcentaje guardado como fracción entre 0 y 1
Rate = Annotated[float, Field(ge=0, le=1)]


class HerdCategoryInput(BaseModel):
    animal_category_id: int
    quantity: int = Field(ge=0)


class HerdData(BaseModel):
    """Datos del rodeo de un sector en una campaña.

    Las reglas que cruzan campos (vacas, entore, terneros) se revisan en el
    servicio, para responder con un mensaje claro.
    """

    categories: list[HerdCategoryInput]
    range_condition: RangeCondition
    replacement_rate: Rate | None = None
    weaning_rate: Rate | None = None
    early_weaning: bool = False
    supplemented: bool = False
    breeding_start: date | None = None
    breeding_end: date | None = None


class HerdCreate(HerdData):
    production_unit_id: int


class HerdRead(HerdData):
    id: int
    season_id: int
    production_unit_id: int
