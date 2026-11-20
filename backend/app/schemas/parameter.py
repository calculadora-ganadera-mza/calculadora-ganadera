from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ParameterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    description: str
    value: float | None
    unit: str
    producer_editable: bool


class ParameterUpdate(BaseModel):
    """Valor nuevo, mayor que 0. Solo los índices aceptan None."""

    value: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None
