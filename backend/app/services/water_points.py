from sqlalchemy import JSON, cast, func, select

from app.models import ProductionUnit, WaterPoint


def read_points(session, unit_id):
    return list(
        session.execute(
            select(
                WaterPoint.id,
                WaterPoint.name,
                WaterPoint.refill_l_day,
                cast(func.ST_AsGeoJSON(WaterPoint.location), JSON).label("location"),
                (~func.ST_Covers(ProductionUnit.polygon, WaterPoint.location)).label(
                    "outside_unit"
                ),
            )
            .join(ProductionUnit)
            .where(WaterPoint.production_unit_id == unit_id)
            .order_by(WaterPoint.created_at, WaterPoint.id)
        ).mappings()
    )


def assign(point, data):
    point.name = data.name
    point.location = func.ST_GeomFromGeoJSON(data.location.model_dump_json())
    point.refill_l_day = data.refill_l_day


class WaterPointNotFoundError(ValueError):
    """El recurso no existe o no pertenece al usuario."""


def owned_unit(session, user_id, unit_id):
    from app.services.production_units import get_user_unit

    unit = get_user_unit(session, user_id, unit_id)
    if unit is None:
        raise WaterPointNotFoundError("Sector no encontrado.")
    return unit


def owned_point(session, user_id, point_id):
    point = session.get(WaterPoint, point_id)
    if point is None:
        raise WaterPointNotFoundError("Aguada no encontrada.")
    owned_unit(session, user_id, point.production_unit_id)
    return point


def list_user_points(session, user_id, unit_id):
    owned_unit(session, user_id, unit_id)
    return read_points(session, unit_id)


def create_point(session, user_id, unit_id, data):
    owned_unit(session, user_id, unit_id)
    point = WaterPoint(production_unit_id=unit_id)
    assign(point, data)
    session.add(point)
    session.commit()
    return next(row for row in read_points(session, unit_id) if row["id"] == point.id)


def update_point(session, user_id, point_id, data):
    point = owned_point(session, user_id, point_id)
    assign(point, data)
    session.commit()
    return next(
        row
        for row in read_points(session, point.production_unit_id)
        if row["id"] == point.id
    )


def delete_point(session, user_id, point_id):
    session.delete(owned_point(session, user_id, point_id))
    session.commit()
