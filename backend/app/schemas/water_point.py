from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.production_unit import Position, UnitName


class PointGeoJSON(BaseModel):
    type: Literal["Point"]
    coordinates: Position


class WaterPointInput(BaseModel):
    name: UnitName
    location: PointGeoJSON
    refill_l_day: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class WaterPointRead(WaterPointInput):
    id: int
    outside_unit: bool
