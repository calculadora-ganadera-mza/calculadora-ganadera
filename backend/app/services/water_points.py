from geoalchemy2 import Geography, WKBElement
from sqlalchemy import JSON, and_, cast, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import aliased

from app.models import ProductionUnit, WaterPoint

WATER_POINT_EDGE_TOLERANCE_M = 5.0


class InvalidWaterPointError(ValueError):
    """Ubicación de aguada fuera de la tolerancia del sector."""


class WaterPointNotFoundError(ValueError):
    """El recurso no existe o no pertenece al usuario."""


def within_sector(location, polygon):
    if isinstance(polygon, WKBElement):
        polygon = func.ST_GeomFromEWKB(bytes.fromhex(polygon.desc))
    return func.ST_DWithin(
        cast(location, Geography(srid=4326)),
        cast(polygon, Geography(srid=4326)),
        WATER_POINT_EDGE_TOLERANCE_M,
    )


def assign(point, data):
    point.shared = data.shared
    point.name = data.name
    point.location = func.ST_GeomFromGeoJSON(data.location.model_dump_json())
    point.refill_l_day = data.refill_l_day


def owned_unit(session, user_id, unit_id, *, for_update=False):
    from app.services.production_units import get_user_unit

    unit = get_user_unit(session, user_id, unit_id, for_update=for_update)
    if unit is None:
        raise WaterPointNotFoundError("Sector no encontrado.")
    return unit


def owned_point(session, user_id, point_id, *, for_update=False):
    point = session.get(WaterPoint, point_id)
    if point is None:
        raise WaterPointNotFoundError("Aguada no encontrada.")
    unit = owned_unit(session, user_id, point.production_unit_id, for_update=for_update)
    return point, unit


def validate_location(session, data, polygon):
    location = func.ST_GeomFromGeoJSON(data.location.model_dump_json())
    if not session.scalar(select(within_sector(location, polygon))):
        raise InvalidWaterPointError(
            "La aguada debe estar dentro de su sector o a menos de 5 m de su borde."
        )


def read_points(session, unit_id=None, *, scenario_id=None):
    """Una consulta para los puntos y todos sus vecinos"""
    neighbor = aliased(ProductionUnit)
    query = (
        select(
            WaterPoint.id,
            WaterPoint.production_unit_id,
            WaterPoint.name,
            WaterPoint.refill_l_day,
            cast(func.ST_AsGeoJSON(WaterPoint.location), JSON).label("location"),
            WaterPoint.shared,
            func.array_remove(
                func.array_agg(aggregate_order_by(neighbor.id, neighbor.id)), None
            ).label("neighbor_unit_ids"),
        )
        .join(ProductionUnit)
        .outerjoin(
            neighbor,
            and_(
                neighbor.scenario_id == ProductionUnit.scenario_id,
                neighbor.id != ProductionUnit.id,
                within_sector(WaterPoint.location, neighbor.polygon),
            ),
        )
        .group_by(WaterPoint.id)
        .order_by(WaterPoint.created_at, WaterPoint.id)
    )
    if unit_id is not None:
        query = query.where(WaterPoint.production_unit_id == unit_id)
    else:
        query = query.where(ProductionUnit.scenario_id == scenario_id)
    return list(session.execute(query).mappings())


def list_user_points(session, user_id, unit_id):
    owned_unit(session, user_id, unit_id)
    return read_points(session, unit_id)


def create_point(session, user_id, unit_id, data):
    # Bloquea y obtiene el contorno actual antes de validar la ubicación.
    unit = owned_unit(session, user_id, unit_id, for_update=True)
    validate_location(session, data, unit.polygon)
    point = WaterPoint(production_unit_id=unit_id)
    assign(point, data)
    session.add(point)
    session.commit()
    return next(row for row in read_points(session, unit_id) if row["id"] == point.id)


def update_point(session, user_id, point_id, data):
    point, unit = owned_point(session, user_id, point_id, for_update=True)
    validate_location(session, data, unit.polygon)
    assign(point, data)
    session.commit()
    return next(
        row
        for row in read_points(session, point.production_unit_id)
        if row["id"] == point.id
    )


def delete_point(session, user_id, point_id):
    point, _ = owned_point(session, user_id, point_id)
    session.delete(point)
    session.commit()
