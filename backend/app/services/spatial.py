"""Predicados y cuentas espaciales compartidos por sectores y aguadas."""

from typing import Any

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    ColumnElement,
    SQLColumnExpression,
    and_,
    case,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.orm import aliased

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


def litres_share(
    owner: type[ProductionUnit], sector: type[ProductionUnit]
) -> ColumnElement[float]:
    """Parte de los litros de la aguada que le toca al sector.

    Una aguada no compartida le da todo a su sector. Una compartida reparte
    según la parte de su alcance que cae en cada sector que abastece. Cada
    parte se divide por la suma de todas, así que entre los sectores reciben
    exactamente los litros de la aguada, aunque se superpongan.
    """
    supplied = aliased(ProductionUnit)
    reach = water_point_reach(WaterPoint.location)
    sector_area = func.ST_Area(
        func.ST_Intersection(reach, cast(sector.polygon, Geography(srid=4326)))
    )
    supplied_area = (
        select(
            func.sum(
                func.ST_Area(
                    func.ST_Intersection(
                        reach, cast(supplied.polygon, Geography(srid=4326))
                    )
                )
            )
        )
        .where(supplies_sector(WaterPoint, owner, supplied))
        .correlate(WaterPoint, owner)
        .scalar_subquery()
    )
    return case(
        (WaterPoint.shared.is_(True), sector_area / func.nullif(supplied_area, 0)),
        else_=1.0,
    )


def sector_refill_l_day(sector: type[ProductionUnit]) -> ColumnElement[float | None]:
    """Litros por día que le tocan al sector, como subconsulta correlacionada.

    Es None si ninguna aguada que lo abastece tiene litros cargados.
    """
    owner = aliased(ProductionUnit)
    return (
        select(func.sum(WaterPoint.refill_l_day * litres_share(owner, sector)))
        .select_from(WaterPoint)
        .join(owner, owner.id == WaterPoint.production_unit_id)
        .where(supplies_sector(WaterPoint, owner, sector))
        .correlate(sector)
        .scalar_subquery()
    )
