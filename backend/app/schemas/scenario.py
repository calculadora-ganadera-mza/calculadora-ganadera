from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Nombre sin espacios al principio ni al final, y no vacío
ScenarioName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ScenarioCreate(BaseModel):
    name: ScenarioName
    first_season_year: int


class SeasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    end_date: date


class ScenarioRead(BaseModel):
    id: int
    name: str
    seasons: list[SeasonRead]


class SeasonYearOption(BaseModel):
    """Un año que se puede elegir para la primera campaña, con sus fechas."""

    start_year: int
    start_date: date
    end_date: date
