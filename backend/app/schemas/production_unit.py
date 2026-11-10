from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
# Una posicion GeoJSON: [longitud, latitud]
Position = tuple[Longitude, Latitude]

# Cada anillo tiene al menos cuatro posiciones: tres puntos y el cierre
Ring = Annotated[list[Position], Field(min_length=4)]

UnitName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class PolygonGeoJSON(BaseModel):
    """Polígono GeoJSON: el primer anillo es el contorno y los siguientes, huecos."""

    type: Literal["Polygon"]
    coordinates: list[Ring] = Field(min_length=1)

    @field_validator("coordinates")
    @classmethod
    def rings_are_closed(cls, rings: list[Ring]) -> list[Ring]:
        if any(ring[0] != ring[-1] for ring in rings):
            raise ValueError(
                "Cada anillo tiene que terminar en el mismo punto en que empieza."
            )
        return rings


class ProductionUnitInput(BaseModel):
    name: UnitName
    polygon: PolygonGeoJSON


class ProductionUnitRead(BaseModel):
    id: int
    name: str
    polygon: PolygonGeoJSON
    area_ha: float
    usable_area_ha: float
