"""Invariantes espaciales con transacciones independientes."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import ProductionUnit, Scenario, User, WaterPoint
from app.schemas.production_unit import PolygonGeoJSON
from app.schemas.water_point import WaterPointInput
from app.services import production_units, water_points


@pytest.fixture
def committed_sector(engine):
    # Las conexiones necesitan datos confirmados, fuera de la fixture de rollback.
    with Session(engine) as session:
        user = User(
            name="Concurrent", email=f"{uuid4()}@example.com", password_hash="x"
        )
        session.add(user)
        session.flush()
        scenario = Scenario(user_id=user.id, name="Concurrent")
        session.add(scenario)
        session.flush()
        unit = production_units.create_unit(
            session,
            scenario.id,
            "Sector",
            PolygonGeoJSON(
                type="Polygon",
                coordinates=[
                    [
                        (-68.09, -34.58),
                        (-68.08, -34.58),
                        (-68.08, -34.57),
                        (-68.09, -34.57),
                        (-68.09, -34.58),
                    ]
                ],
            ),
        )
        user_id, unit_id = user.id, unit.id
        session.commit()
    try:
        yield user_id, unit_id
    finally:
        with Session(engine) as session:
            session.delete(session.get(User, user_id))
            session.commit()


@pytest.mark.parametrize("operation", ["create", "move"])
@pytest.mark.parametrize("first", ["water", "shape"])
def test_water_and_contour_changes_are_serialized(
    engine, committed_sector, monkeypatch, operation, first
):
    user_id, unit_id = committed_sector
    point_id = None
    if operation == "move":
        with Session(engine) as seed:
            point = WaterPoint(
                production_unit_id=unit_id,
                name="Original",
                location="SRID=4326;POINT(-68.082 -34.575)",
            )
            seed.add(point)
            seed.flush()
            point_id = point.id
            seed.commit()
    # El original cabe en ambos contornos; el nuevo solo cabe en el viejo.
    new_contour = PolygonGeoJSON(
        type="Polygon",
        coordinates=[
            [
                (-68.085, -34.58),
                (-68.08, -34.58),
                (-68.08, -34.57),
                (-68.085, -34.57),
                (-68.085, -34.58),
            ]
        ],
    )
    data = WaterPointInput(
        name="Nueva",
        location={
            "type": "Point",
            "coordinates": [-68.088, -34.575],
        },
    )
    ready = {role: Event() for role in ("water", "shape")}
    start = {role: Event() for role in ("water", "shape")}
    first_locked, release = Event(), Event()
    pids = {}
    original_assign = water_points.assign

    def pause_water(point, values):
        original_assign(point, values)
        if first == "water":
            first_locked.set()
            assert release.wait(10)

    monkeypatch.setattr(water_points, "assign", pause_water)

    def run(role):
        with Session(engine) as session:
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            pids[role] = session.scalar(select(text("pg_backend_pid()")))
            # Precargar también prueba que se refresque el identity map obsoleto.
            unit = production_units.get_user_unit(session, user_id, unit_id)
            ready[role].set()
            assert start[role].wait(10)
            try:
                if role == "water":
                    if operation == "create":
                        water_points.create_point(session, user_id, unit_id, data)
                    else:
                        water_points.update_point(session, user_id, point_id, data)
                else:
                    production_units.update_unit(
                        session, unit, "Recortado", new_contour
                    )
                    if first == "shape":
                        first_locked.set()
                        assert release.wait(10)
                    session.commit()
                return "saved"
            except (
                production_units.InvalidPolygonError,
                water_points.InvalidWaterPointError,
            ):
                session.rollback()
                return "invalid"

    second = "shape" if first == "water" else "water"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {role: pool.submit(run, role) for role in ("water", "shape")}
        try:
            assert all(event.wait(10) for event in ready.values())
            start[first].set()
            assert first_locked.wait(10)
            start[second].set()
            # Se observa el bloqueo real: no se depende de acertar un intervalo.
            with engine.connect() as monitor:
                deadline = monotonic() + 4
                while True:
                    blockers = monitor.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": pids[second]}
                    )
                    if pids[first] in blockers:
                        break
                    assert not futures[second].done(), "No esperó el bloqueo del sector"
                    assert monotonic() < deadline, "No se observó el bloqueo"
                    release.wait(0.01)
            release.set()
            assert futures[first].result(timeout=10) == "saved"
            assert futures[second].result(timeout=10) == "invalid"
        finally:
            release.set()
            for event in start.values():
                event.set()
    with Session(engine) as check:
        valid = list(
            check.scalars(
                select(
                    water_points.within_sector(
                        WaterPoint.location, ProductionUnit.polygon
                    )
                )
                .select_from(WaterPoint)
                .join(ProductionUnit)
                .where(ProductionUnit.id == unit_id)
            )
        )
        assert len(valid) == (0 if operation == "create" and first == "shape" else 1)
        assert all(valid)
