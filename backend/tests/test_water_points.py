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
    assert first.json()["outside_unit"] is False
    second = api.post(path, json=data).json()
    covered = api.get(f"/scenarios/{scenario.id}/production-units").json()[0]
    assert covered["usable_area_ha"] == pytest.approx(sector["area_ha"], rel=0.001)
    assert covered["usable_geometry"]["type"] == "MultiPolygon"
    assert api.delete(f"/water-points/{second['id']}").status_code == 204
    data["location"]["coordinates"] = [-68.095, -34.575]
    outside = api.put(f"/water-points/{first.json()['id']}", json=data)
    assert outside.status_code == 200
    assert outside.json()["outside_unit"] is True
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


def test_boundary_radius_and_polygon_changes(api, session, unit):
    from sqlalchemy import select

    from app.models import Parameter

    scenario, sector = unit
    path = f"/production-units/{sector['id']}/water-points"
    data = {
        "name": "Límite",
        "location": {"type": "Point", "coordinates": [-68.09, -34.58]},
    }
    assert api.post(path, json=data).json()["outside_unit"] is False
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
    assert changed.json()["usable_area_ha"] == 0
    assert api.get(path).json()[0]["outside_unit"] is True
