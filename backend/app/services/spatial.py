"""Predicados espaciales compartidos por sectores y aguadas."""

from typing import Any

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import ColumnElement, SQLColumnExpression, and_, cast, func, or_

from app.models import ProductionUnit, WaterPoint
from app.services.parameters import select_parameter

WATER_POINT_EDGE_TOLERANCE_M = 5.0


def within_sector(
    location: SQLColumnExpression[Any],
    polygon: SQLColumnExpression[Any] | WKBElement,
) -> ColumnElement[bool]:
    if isinstance(polygon, WKBElement):
        polygon = func.ST_GeomFromEWKB(bytes.fromhex(polygon.desc))
    return func.ST_DWithin(
        cast(location, Geography(srid=4326)),
        cast(polygon, Geography(srid=4326)),
        WATER_POINT_EDGE_TOLERANCE_M,
    )


def water_point_reach(location: SQLColumnExpression[Any]) -> ColumnElement[Any]:
    """Círculo del alcance de una aguada, en geography."""
    radius = select_parameter("water_point_radius_km").scalar_subquery()
    return func.ST_Buffer(cast(location, Geography(srid=4326)), radius * 1000, 32)


def supplies_sector(
    point: type[WaterPoint],
    owner: type[ProductionUnit],
    sector: type[ProductionUnit],
) -> ColumnElement[bool]:
    """La aguada abastece al sector: es suya, o es compartida, está sobre su
    borde y los dos sectores son del mismo escenario."""
    return or_(
        point.production_unit_id == sector.id,
        and_(
            point.shared.is_(True),
            owner.scenario_id == sector.scenario_id,
            within_sector(point.location, sector.polygon),
        ),
    )
