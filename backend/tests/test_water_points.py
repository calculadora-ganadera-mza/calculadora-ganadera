import pytest

from app.models import Scenario


@pytest.fixture
def unit(api, session, user):
    scenario = Scenario(user_id=user.id, name="Campo", is_main=True)
    session.add(scenario)
    session.flush()
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-68.09, -34.58],
                [-68.08, -34.58],
                [-68.08, -34.57],
                [-68.09, -34.57],
                [-68.09, -34.58],
            ]
        ],
    }
    response = api.post(
        f"/scenarios/{scenario.id}/production-units",
        json={"name": "Sector", "polygon": polygon},
    )
    assert response.status_code == 201
    return scenario, response.json()


def test_coverage_overlap_and_crud(api, unit):
    scenario, sector = unit
    path = f"/production-units/{sector['id']}/water-points"
    assert sector["usable_area_ha"] == 0
    data = {
        "name": "Tanque",
        "location": {"type": "Point", "coordinates": [-68.085, -34.575]},
    }
    first = api.post(path, json=data)
    assert first.status_code == 201
    assert first.json()["shared"] is False
    second = api.post(path, json=data).json()
    covered = api.get(f"/scenarios/{scenario.id}/production-units").json()[0]
    assert covered["usable_area_ha"] == pytest.approx(sector["area_ha"], rel=0.001)
    assert covered["usable_geometry"]["type"] == "MultiPolygon"
    assert api.delete(f"/water-points/{second['id']}").status_code == 204
    data["location"]["coordinates"] = [-68.095, -34.575]
    outside = api.put(f"/water-points/{first.json()['id']}", json=data)
    assert outside.status_code == 422
    assert (
        api.get(f"/scenarios/{scenario.id}/production-units").json()[0][
            "usable_area_ha"
        ]
        > 0
    )
    assert api.delete(f"/water-points/{first.json()['id']}").status_code == 204
    assert (
        api.get(f"/scenarios/{scenario.id}/production-units").json()[0][
            "usable_area_ha"
        ]
        == 0
    )


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_refill(api, unit, value):
    _, sector = unit
    response = api.post(
        f"/production-units/{sector['id']}/water-points",
        json={
            "name": "Agua",
            "location": {"type": "Point", "coordinates": [-68, -34]},
            "refill_l_day": value,
        },
    )
    assert response.status_code == 422


def test_foreign_point_hidden(api, session, other_user):
    from app.models import WaterPoint
    from app.schemas.production_unit import PolygonGeoJSON
    from app.services.production_units import create_unit

    scenario = Scenario(user_id=other_user.id, name="Ajeno", is_main=True)
    session.add(scenario)
    session.flush()
    sector = create_unit(
        session,
        scenario.id,
        "Ajeno",
        PolygonGeoJSON(
            type="Polygon",
            coordinates=[[(-68, -34), (-67, -34), (-67, -33), (-68, -34)]],
        ),
    )
    point = WaterPoint(
        production_unit_id=sector.id, name="Ajena", location="SRID=4326;POINT(-68 -34)"
    )
    session.add(point)
    session.flush()
    assert api.get(f"/production-units/{sector.id}/water-points").status_code == 404
    assert api.delete(f"/water-points/{point.id}").status_code == 404
    data = {"name": "Ajena", "location": {"type": "Point", "coordinates": [-68, -34]}}
    assert (
        api.post(f"/production-units/{sector.id}/water-points", json=data).status_code
        == 404
    )
    assert api.put(f"/water-points/{point.id}", json=data).status_code == 404


def test_boundary_radius_and_polygon_changes(api, session, unit):
    from sqlalchemy import select

    from app.models import Parameter

    scenario, sector = unit
    path = f"/production-units/{sector['id']}/water-points"
    data = {
        "name": "Límite",
        "location": {"type": "Point", "coordinates": [-68.09, -34.58]},
    }
    assert api.post(path, json=data).json()["shared"] is False
    radius = session.scalar(
        select(Parameter).where(Parameter.key == "water_point_radius_km")
    )
    radius.value = 0.1
    session.flush()
    covered = api.get(f"/scenarios/{scenario.id}/production-units").json()[0]
    assert 0 < covered["usable_area_ha"] < sector["area_ha"]
    # Un segundo sector no hereda la aguada del primero.
    other = api.post(
        f"/scenarios/{scenario.id}/production-units",
        json={"name": "Otro", "polygon": sector["polygon"]},
    )
    assert other.json()["usable_area_ha"] == 0
    moved = {
        "type": "Polygon",
        "coordinates": [[[-67, -34], [-66.99, -34], [-66.99, -33.99], [-67, -34]]],
    }
    changed = api.put(
        f"/production-units/{sector['id']}", json={"name": "Sector", "polygon": moved}
    )
    assert changed.status_code == 422
    assert "Límite" in changed.json()["detail"]


@pytest.mark.parametrize("offset,status", [(0, 201), (-0.00003, 201), (-0.00011, 422)])
def test_edge_tolerance(api, unit, offset, status):
    _, sector = unit
    response = api.post(
        f"/production-units/{sector['id']}/water-points",
        json={
            "name": "Borde",
            "location": {"type": "Point", "coordinates": [-68.085, -34.58 + offset]},
        },
    )
    assert response.status_code == status


def test_shared_neighbors_and_dynamic_contours(api, unit):
    scenario, sector = unit
    neighbor_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-68.08, -34.58],
                [-68.07, -34.58],
                [-68.07, -34.57],
                [-68.08, -34.57],
                [-68.08, -34.58],
            ]
        ],
    }
    neighbor = api.post(
        f"/scenarios/{scenario.id}/production-units",
        json={"name": "Vecino", "polygon": neighbor_polygon},
    ).json()
    distant = api.post(
        f"/scenarios/{scenario.id}/production-units",
        json={
            "name": "Lejano",
            "polygon": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-68.069, -34.58],
                        [-68.06, -34.58],
                        [-68.06, -34.57],
                        [-68.069, -34.58],
                    ]
                ],
            },
        },
    ).json()
    data = {
        "name": "Compartida",
        "location": {"type": "Point", "coordinates": [-68.08, -34.575]},
        "shared": False,
    }
    point = api.post(f"/production-units/{sector['id']}/water-points", json=data).json()
    assert point["neighbor_unit_ids"] == [neighbor["id"]]

    def areas():
        return {
            u["id"]: u["usable_area_ha"]
            for u in api.get(f"/scenarios/{scenario.id}/production-units").json()
        }

    assert areas()[neighbor["id"]] == 0
    data["shared"] = True
    assert api.put(f"/water-points/{point['id']}", json=data).status_code == 200
    assert areas()[sector["id"]] > 0
    assert areas()[neighbor["id"]] > 0
    assert areas()[distant["id"]] == 0
    moved = {
        "type": "Polygon",
        "coordinates": [[[-67, -34], [-66.99, -34], [-66.99, -33.99], [-67, -34]]],
    }
    assert (
        api.put(
            f"/production-units/{neighbor['id']}",
            json={"name": "Vecino", "polygon": moved},
        ).status_code
        == 200
    )
    assert (
        api.get(f"/production-units/{sector['id']}/water-points").json()[0][
            "neighbor_unit_ids"
        ]
        == []
    )
    assert areas()[neighbor["id"]] == 0
    rejected = api.put(
        f"/production-units/{sector['id']}", json={"name": "Dueño", "polygon": moved}
    )
    assert rejected.status_code == 422
    assert "Compartida" in rejected.json()["detail"]
    assert (
        api.get(f"/scenarios/{scenario.id}/production-units").json()[0]["polygon"]
        == sector["polygon"]
    )


def test_partial_overlap_and_successful_move(api, session, unit):
    from math import acos, pi, sqrt

    from sqlalchemy import func, select

    from app.models import Parameter

    scenario, sector = unit
    radius = session.scalar(
        select(Parameter).where(Parameter.key == "water_point_radius_km")
    )
    radius.value = 0.1
    session.flush()
    path = f"/production-units/{sector['id']}/water-points"
    centers = [(-68.086, -34.575), (-68.085, -34.575)]
    points = []
    for i, center in enumerate(centers):
        response = api.post(
            path,
            json={
                "name": f"Tanque {i}",
                "location": {"type": "Point", "coordinates": center},
            },
        )
        assert response.status_code == 201
        points.append(response.json())
    # Unión analítica de dos discos de 100 m, independiente del buffer/union.
    distance = session.scalar(
        select(
            func.ST_Distance(
                func.ST_GeogFromText("POINT(-68.086 -34.575)"),
                func.ST_GeogFromText("POINT(-68.085 -34.575)"),
            )
        )
    )
    overlap = 20000 * acos(distance / 200) - distance / 2 * sqrt(40000 - distance**2)
    expected = (2 * pi * 10000 - overlap) / 10000
    covered = api.get(f"/scenarios/{scenario.id}/production-units").json()[0]
    assert 0 < covered["usable_area_ha"] < sector["area_ha"]
    assert covered["usable_area_ha"] == pytest.approx(expected, rel=0.005)
    response = api.put(
        f"/water-points/{points[0]['id']}",
        json={
            "name": "Movida",
            "location": {"type": "Point", "coordinates": [-68.09, -34.58]},
        },
    )
    assert response.status_code == 200
    assert response.json()["location"]["coordinates"] == [-68.09, -34.58]
    moved = api.get(f"/scenarios/{scenario.id}/production-units").json()[0]
    # Un cuarto de disco en el vértice más el disco del segundo punto, separado.
    assert moved["usable_area_ha"] == pytest.approx(1.25 * pi, rel=0.01)
    assert moved["usable_area_ha"] < covered["usable_area_ha"]


def test_scenario_points_batch_and_constant_query_count(api, session, unit, other_user):
    from sqlalchemy import event

    from app.services.water_points import read_points

    scenario, sector = unit
    path = f"/production-units/{sector['id']}/water-points"
    counts = []
    connection = session.connection()
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    for size in (1, 20):
        for index in range(size - (1 if size == 20 else 0)):
            assert (
                api.post(
                    path,
                    json={
                        "name": f"Tanque {size}-{index}",
                        "location": {
                            "type": "Point",
                            "coordinates": [-68.085, -34.575],
                        },
                    },
                ).status_code
                == 201
            )
        scenario_id = scenario.id
        statements.clear()
        event.listen(connection, "before_cursor_execute", record)
        try:
            rows = read_points(session, scenario_id=scenario_id)
        finally:
            event.remove(connection, "before_cursor_execute", record)
        assert len(rows) == size
        assert all(row["neighbor_unit_ids"] == [] for row in rows)
        counts.append(len(statements))
    assert counts == [1, 1]
    response = api.get(f"/scenarios/{scenario.id}/water-points")
    assert response.status_code == 200
    assert len(response.json()) == 20
    assert all(point["production_unit_id"] == sector["id"] for point in response.json())
    foreign = Scenario(user_id=other_user.id, name="Ajeno", is_main=True)
    session.add(foreign)
    session.flush()
    assert api.get(f"/scenarios/{foreign.id}/water-points").status_code == 404
