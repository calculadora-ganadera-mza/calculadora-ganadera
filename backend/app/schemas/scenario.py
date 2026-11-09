from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Nombre sin espacios al principio ni al final, de 1 a 100 caracteres
ScenarioName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ScenarioCreate(BaseModel):
    name: ScenarioName
    first_season_start_year: int


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_main: bool


class SeasonRead(BaseModel):
    id: int
    start_year: int
    start_date: date
    end_date: date
    rainfall_mm: float | None
    is_current: bool


class SeasonYearOption(BaseModel):
    """Un año que se puede elegir para la primera campaña, con sus fechas."""

    start_year: int
    start_date: date
    end_date: date
