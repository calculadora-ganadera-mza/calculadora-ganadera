from typing import Any

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    JSON,
    ColumnElement,
    Select,
    case,
    cast,
    func,
    select,
    true,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.models import Parameter, ProductionUnit, Scenario, WaterPoint
from app.models.enums import ProductionSystem
from app.schemas.production_unit import PolygonGeoJSON


class InvalidPolygonError(ValueError):
    """El contorno no forma un polígono válido, por ejemplo porque se cruza."""


def to_geometry(session: Session, polygon: PolygonGeoJSON) -> ColumnElement[Any]:
    """Convierte el GeoJSON en geometria de PostGIS, si el contorno es válido.

    Se revisa antes de guardar para devolver un mensaje claro, en lugar del
    error de la restriccion polygon_valid de la tabla.
    """
    geometry = func.ST_GeomFromGeoJSON(polygon.model_dump_json())
    if not session.scalar(select(func.ST_IsValid(geometry))):
        raise InvalidPolygonError(
            "El contorno no es válido: no puede cruzarse consigo mismo."
        )
    return geometry


def select_units() -> Select:
    """Sectores con el contorno en GeoJSON, tal como los devuelve la API."""
    buffered_water = cast(
        func.ST_Buffer(
            cast(WaterPoint.location, Geography(srid=4326)),
            Parameter.value * 1000,
            32,
        ),
        Geometry(srid=4326),
    )
    coverage = (
        select(
            func.ST_Multi(
                func.ST_CollectionExtract(
                    func.ST_Intersection(
                        ProductionUnit.polygon, func.ST_Union(buffered_water)
                    ),
                    3,
                )
            ).label("geom")
        )
        .select_from(WaterPoint)
        .join(Parameter, true())
        .where(
            WaterPoint.production_unit_id == ProductionUnit.id,
            Parameter.key == "water_point_radius_km",
        )
        .correlate(ProductionUnit)
        .lateral("coverage")
    )
    return (
        select(
            ProductionUnit.id,
            ProductionUnit.name,
            cast(func.ST_AsGeoJSON(ProductionUnit.polygon), JSON).label("polygon"),
            ProductionUnit.area_ha,
            func.coalesce(
                func.ST_Area(cast(coverage.c.geom, Geography(srid=4326))) / 10000,
                0,
            ).label("usable_area_ha"),
            case(
                (func.ST_IsEmpty(coverage.c.geom), None),
                else_=cast(func.ST_AsGeoJSON(coverage.c.geom), JSON),
            ).label("usable_geometry"),
        )
        .select_from(ProductionUnit)
        .join(coverage, true(), isouter=True)
    )


def list_units(session: Session, scenario_id: int) -> list[RowMapping]:
    """Sectores del establecimiento, ordenados por fecha de creación."""
    query = (
        select_units()
        .where(ProductionUnit.scenario_id == scenario_id)
        .order_by(ProductionUnit.created_at, ProductionUnit.id)
    )
    return list(session.execute(query).mappings())


def read_unit(session: Session, unit_id: int) -> RowMapping:
    """Un sector, en el formato de la API."""
    query = select_units().where(ProductionUnit.id == unit_id)
    return session.execute(query).mappings().one()


def get_user_unit(
    session: Session, user_id: int, unit_id: int
) -> ProductionUnit | None:
    """El sector, solo si es de un establecimiento del usuario."""
    return session.scalar(
        select(ProductionUnit)
        .join(Scenario)
        .where(ProductionUnit.id == unit_id, Scenario.user_id == user_id)
    )


def create_unit(
    session: Session, scenario_id: int, name: str, polygon: PolygonGeoJSON
) -> ProductionUnit:
    """Crea el sector, siempre de secano.

    La API no recibe el ambiente.
    """
    unit = ProductionUnit(
        scenario_id=scenario_id,
        name=name,
        production_system=ProductionSystem.RAINFED,
        polygon=to_geometry(session, polygon),
    )
    session.add(unit)
    session.flush()
    return unit


def update_unit(
    session: Session, unit: ProductionUnit, name: str, polygon: PolygonGeoJSON
) -> None:
    """Cambia el nombre y el contorno."""
    unit.name = name
    unit.polygon = to_geometry(session, polygon)
    session.flush()
