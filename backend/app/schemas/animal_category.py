from pydantic import BaseModel, ConfigDict


class AnimalCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    cow_equivalent: float
    summer_water_l_day: float
    winter_water_l_day: float
