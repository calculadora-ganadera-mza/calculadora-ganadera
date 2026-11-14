from typing import Any

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    JSON,
    ColumnElement,
    Select,
    and_,
    case,
    cast,
    func,
    or_,
    select,
    true,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, aliased

from app.models import Parameter, ProductionUnit, Scenario, WaterPoint
from app.models.enums import ProductionSystem
from app.schemas.production_unit import PolygonGeoJSON
from app.services.water_points import within_sector


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
    owner = aliased(ProductionUnit)
    coverage = (
        select(
            func.ST_Multi(
                func.ST_CollectionExtract(
                    cast(
                        func.ST_Intersection(
                            cast(ProductionUnit.polygon, Geography(srid=4326)),
                            cast(func.ST_Union(buffered_water), Geography(srid=4326)),
                        ),
                        Geometry(srid=4326),
                    ),
                    3,
                )
            ).label("geom")
        )
        .select_from(WaterPoint)
        .join(Parameter, true())
        .join(owner, owner.id == WaterPoint.production_unit_id)
        .where(
            or_(
                WaterPoint.production_unit_id == ProductionUnit.id,
                and_(
                    WaterPoint.shared.is_(True),
                    owner.scenario_id == ProductionUnit.scenario_id,
                    within_sector(WaterPoint.location, ProductionUnit.polygon),
                ),
            ),
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
    session: Session, user_id: int, unit_id: int, *, for_update: bool = False
) -> ProductionUnit | None:
    """El sector, solo si es de un establecimiento del usuario."""
    query = (
        select(ProductionUnit)
        .join(Scenario)
        .where(ProductionUnit.id == unit_id, Scenario.user_id == user_id)
    )
    if for_update:
        query = query.with_for_update(of=ProductionUnit).execution_options(
            populate_existing=True
        )
    return session.scalar(query)


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
    session.refresh(unit, with_for_update=True)
    geometry = to_geometry(session, polygon)
    outside = list(
        session.scalars(
            select(WaterPoint.name).where(
                WaterPoint.production_unit_id == unit.id,
                ~within_sector(WaterPoint.location, geometry),
            )
        )
    )
    if outside:
        raise InvalidPolygonError(
            "El contorno deja afuera estas aguadas: "
            + ", ".join(outside)
            + ". Borrá esas aguadas primero."
        )
    unit.name = name
    unit.polygon = geometry
    session.flush()
