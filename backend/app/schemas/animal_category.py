from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class AnimalCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    cow_equivalent: float
    summer_water_l_day: float
    winter_water_l_day: float


class AnimalCategoryUpdate(BaseModel):
    """Campos que cambia el administrador; el código no se edita."""

    name: CategoryName | None = None
    cow_equivalent: Positive | None = None
    summer_water_l_day: Positive | None = None
    winter_water_l_day: Positive | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AnimalCategoryUpdate:
        if not self.model_fields_set:
            raise ValueError("Hay que enviar al menos un campo.")
        return self
