from dataclasses import dataclass

from geoalchemy2 import Geography, Geometry, WKBElement
from sqlalchemy import (
    JSON,
    and_,
    cast,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, aliased

from app.models import ProductionUnit, WaterPoint
from app.schemas.water_point import WaterPointInput
from app.services.production_units import get_user_unit
from app.services.spatial import (
    WATER_POINT_EDGE_TOLERANCE_M,
    litres_share,
    supplies_sector,
    water_point_reach,
    within_sector,
)


class InvalidWaterPointError(ValueError):
    """Ubicación de aguada fuera de la tolerancia del sector."""


class WaterPointNotFoundError(ValueError):
    """El recurso no existe o no pertenece al usuario."""


@dataclass(frozen=True)
class AvailableWater:
    """Litros por día que le tocan a un sector."""

    # None si ninguna aguada que cuenta tiene litros cargados
    refill_l_day: float | None
    # Hay aguadas que cuenta para el sector y no tienen litros cargados
    partial: bool


def available_water(session: Session, unit_id: int) -> AvailableWater:
    """Litros por día de las aguadas que abastecen al sector."""
    owner = aliased(ProductionUnit)
    sector = aliased(ProductionUnit)
    refill, points, with_litres = session.execute(
        select(
            func.sum(WaterPoint.refill_l_day * litres_share(owner, sector)),
            func.count(),
            func.count(WaterPoint.refill_l_day),
        )
        .select_from(WaterPoint)
        .join(owner, owner.id == WaterPoint.production_unit_id)
        .join(sector, supplies_sector(WaterPoint, owner, sector))
        .where(sector.id == unit_id)
    ).one()
    return AvailableWater(refill_l_day=refill, partial=0 < with_litres < points)


def assign(point: WaterPoint, data: WaterPointInput) -> None:
    point.shared = data.shared
    point.name = data.name
    point.location = func.ST_GeomFromGeoJSON(data.location.model_dump_json())
    point.refill_l_day = data.refill_l_day


def owned_unit(
    session: Session, user_id: int, unit_id: int, *, for_update: bool = False
) -> ProductionUnit:
    unit = get_user_unit(session, user_id, unit_id, for_update=for_update)
    if unit is None:
        raise WaterPointNotFoundError("Sector no encontrado.")
    return unit


def owned_point(
    session: Session, user_id: int, point_id: int, *, for_update: bool = False
) -> tuple[WaterPoint, ProductionUnit]:
    point = session.get(WaterPoint, point_id)
    if point is None:
        raise WaterPointNotFoundError("Aguada no encontrada.")
    unit = owned_unit(session, user_id, point.production_unit_id, for_update=for_update)
    return point, unit


def validate_location(
    session: Session, data: WaterPointInput, polygon: WKBElement
) -> None:
    location = func.ST_GeomFromGeoJSON(data.location.model_dump_json())
    if not session.scalar(select(within_sector(location, polygon))):
        raise InvalidWaterPointError(
            "La aguada debe estar dentro de su sector o a menos de "
            f"{WATER_POINT_EDGE_TOLERANCE_M:g} m de su borde."
        )


def read_points(
    session: Session, unit_id: int | None = None, *, scenario_id: int | None = None
) -> list[RowMapping]:
    """Una consulta para los puntos y todos sus vecinos"""
    neighbor = aliased(ProductionUnit)
    # Calcula únicamente el aporte de esta aguada en los vecinos habilitados.
    coverage_neighbor = aliased(ProductionUnit)
    reach = water_point_reach(WaterPoint.location)
    shared_coverage = (
        select(
            cast(
                func.ST_AsGeoJSON(
                    func.ST_Multi(
                        func.ST_CollectionExtract(
                            func.ST_Union(
                                cast(
                                    func.ST_Intersection(
                                        cast(
                                            coverage_neighbor.polygon,
                                            Geography(srid=4326),
                                        ),
                                        reach,
                                    ),
                                    Geometry(srid=4326),
                                )
                            ),
                            3,
                        )
                    )
                ),
                JSON,
            )
        )
        .where(
            WaterPoint.shared.is_(True),
            coverage_neighbor.scenario_id == ProductionUnit.scenario_id,
            coverage_neighbor.id != ProductionUnit.id,
            within_sector(WaterPoint.location, coverage_neighbor.polygon),
        )
        .correlate(WaterPoint, ProductionUnit)
        .scalar_subquery()
    )
    query = (
        select(
            WaterPoint.id,
            WaterPoint.production_unit_id,
            WaterPoint.name,
            WaterPoint.refill_l_day,
            cast(func.ST_AsGeoJSON(WaterPoint.location), JSON).label("location"),
            WaterPoint.shared,
            shared_coverage.label("shared_coverage_geometry"),
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
        .group_by(WaterPoint.id, ProductionUnit.id)
        .order_by(WaterPoint.created_at, WaterPoint.id)
    )
    if unit_id is not None:
        query = query.where(WaterPoint.production_unit_id == unit_id)
    else:
        query = query.where(ProductionUnit.scenario_id == scenario_id)
    return list(session.execute(query).mappings())


def list_user_points(session: Session, user_id: int, unit_id: int) -> list[RowMapping]:
    owned_unit(session, user_id, unit_id)
    return read_points(session, unit_id)


def create_point(
    session: Session, user_id: int, unit_id: int, data: WaterPointInput
) -> RowMapping:
    # Bloquea y obtiene el contorno actual antes de validar la ubicación.
    unit = owned_unit(session, user_id, unit_id, for_update=True)
    validate_location(session, data, unit.polygon)
    point = WaterPoint(production_unit_id=unit_id)
    assign(point, data)
    session.add(point)
    session.commit()
    return next(row for row in read_points(session, unit_id) if row["id"] == point.id)


def update_point(
    session: Session, user_id: int, point_id: int, data: WaterPointInput
) -> RowMapping:
    point, unit = owned_point(session, user_id, point_id, for_update=True)
    validate_location(session, data, unit.polygon)
    assign(point, data)
    session.commit()
    return next(
        row
        for row in read_points(session, point.production_unit_id)
        if row["id"] == point.id
    )


def delete_point(session: Session, user_id: int, point_id: int) -> None:
    point, _ = owned_point(session, user_id, point_id)
    session.delete(point)
    session.commit()
