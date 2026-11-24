from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Nombre sin espacios al principio ni al final, de 1 a 100 caracteres
ScenarioName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ScenarioCreate(BaseModel):
    name: ScenarioName
    first_season_start_year: int


class ScenarioUpdate(BaseModel):
    """Cambios en un establecimiento: renombrarlo o marcarlo como principal."""

    name: ScenarioName | None = None
    is_main: Literal[True] | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> ScenarioUpdate:
        if not self.model_fields_set:
            raise ValueError("Hay que enviar al menos un campo.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("El nombre no puede quedar vacío.")
        if "is_main" in self.model_fields_set and self.is_main is None:
            raise ValueError("Solo se admite marcar como principal.")
        return self


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


class SeasonUpdate(BaseModel):
    """Lluvia de la campaña anterior, en milímetros; None la elimina."""

    rainfall_mm: float | None = Field(ge=0)


class SeasonCreate(BaseModel):
    """Año de inicio de la campaña nueva.

    El tope evita fechas que Python no puede representar; el fin de la
    campaña cae en el año siguiente.
    """

    start_year: int = Field(ge=1, le=9998)
