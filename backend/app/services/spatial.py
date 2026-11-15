"""Predicados espaciales compartidos por sectores y aguadas."""

from typing import Any

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import ColumnElement, SQLColumnExpression, cast, func

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
