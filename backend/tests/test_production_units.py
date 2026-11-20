import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Scenario, User
from app.schemas.production_unit import PolygonGeoJSON
from app.services.production_units import create_unit


def rectangle(
    width_deg: float,
    height_deg: float,
    *,
    west: float = -68.09,
    south: float = -34.58,
) -> dict:
    """Rectángulo en San Rafael."""
    east, north = west + width_deg, south + height_deg
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


# 0,01° de longitud a 34,6° de latitud son unos 0,917 km, y 0,01° de latitud,
# unos 1,110 km: 0,917 x 1,110 ≈ 1,018 km² ≈ 101,8 ha.
SQUARE = rectangle(0.01, 0.01)
SQUARE_HA = 101.8
# El doble de ancho: el doble de superficie
WIDE = rectangle(0.02, 0.01)
WIDE_HA = 203.6

# Contorno en forma de moño: el segundo lado cruza al cuarto.
BOWTIE = {
    "type": "Polygon",
    "coordinates": [
        [
            [-68.09, -34.58],
            [-68.08, -34.57],
            [-68.08, -34.58],
            [-68.09, -34.57],
            [-68.09, -34.58],
        ]
    ],
}


@pytest.fixture
def scenario(session: Session, user: User) -> Scenario:
    scenario = Scenario(user_id=user.id, name="La Esperanza", is_main=True)
    session.add(scenario)
    session.flush()
    return scenario


@pytest.fixture
def other_scenario(session: Session, other_user: User) -> Scenario:
    scenario = Scenario(user_id=other_user.id, name="Ajeno", is_main=True)
    session.add(scenario)
    session.flush()
    return scenario


def units_url(scenario: Scenario) -> str:
    return f"/scenarios/{scenario.id}/production-units"


def test_draw_unit_returns_its_area(api: TestClient, scenario: Scenario):
    response = api.post(
        units_url(scenario), json={"name": "  Potrero 1 ", "polygon": SQUARE}
    )

    assert response.status_code == 201
    unit = response.json()
    assert unit["name"] == "Potrero 1"
    assert unit["polygon"] == SQUARE
    assert unit["area_ha"] == pytest.approx(SQUARE_HA, rel=0.01)
    # Todavía no se calcula: depende de las aguadas del sector.
    assert unit["usable_area_ha"] == 0


def test_list_units_in_creation_order(api: TestClient, scenario: Scenario):
    for name, polygon in [
        ("Oeste", SQUARE),
        ("Este", rectangle(0.01, 0.01, west=-68.08)),
    ]:
        response = api.post(
            units_url(scenario), json={"name": name, "polygon": polygon}
        )
        assert response.status_code == 201

    response = api.get(units_url(scenario))

    assert response.status_code == 200
    assert [unit["name"] for unit in response.json()] == ["Oeste", "Este"]


def test_edit_unit_recalculates_area(api: TestClient, scenario: Scenario):
    unit = api.post(
        units_url(scenario), json={"name": "Potrero", "polygon": SQUARE}
    ).json()

    response = api.put(
        f"/production-units/{unit['id']}",
        json={"name": "Potrero grande", "polygon": WIDE},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Potrero grande"
    assert response.json()["area_ha"] == pytest.approx(WIDE_HA, rel=0.01)


def test_self_crossing_outline_is_rejected(api: TestClient, scenario: Scenario):
    response = api.post(units_url(scenario), json={"name": "Moño", "polygon": BOWTIE})

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "El contorno no es válido: no puede cruzarse consigo mismo."
    )


def test_edit_with_self_crossing_outline_is_rejected(
    api: TestClient, scenario: Scenario
):
    unit = api.post(
        units_url(scenario), json={"name": "Potrero", "polygon": SQUARE}
    ).json()

    response = api.put(
        f"/production-units/{unit['id']}", json={"name": "Potrero", "polygon": BOWTIE}
    )

    assert response.status_code == 422
    assert api.get(units_url(scenario)).json()[0]["polygon"] == SQUARE


@pytest.mark.parametrize("method", ["POST", "PUT"])
@pytest.mark.parametrize(
    ("west", "accepted"),
    [
        pytest.param(-68.09, False, id="identical"),
        pytest.param(-68.085, False, id="overlap"),
        pytest.param(-68.080002, False, id="over-tolerance"),
        pytest.param(-68.0800005, True, id="under-tolerance"),
        pytest.param(-68.08, True, id="shared-edge"),
    ],
)
def test_sector_overlap_in_same_scenario(
    api: TestClient, scenario: Scenario, method: str, west: float, accepted: bool
):
    path = units_url(scenario)
    existing = api.post(path, json={"name": "El bajo", "polygon": SQUARE})
    assert existing.status_code == 201
    before = [existing.json()]
    if method == "PUT":
        original = rectangle(0.01, 0.01, west=-68.05)
        edited = api.post(path, json={"name": "El alto", "polygon": original})
        assert edited.status_code == 201
        before.append(edited.json())
        path = f"/production-units/{edited.json()['id']}"

    # El borde mide unos 1.110 m. Las franjas finas tienen unos 51 y 204 m².
    polygon = rectangle(0.01, 0.01, west=west)
    response = api.request(method, path, json={"name": "El alto", "polygon": polygon})

    if accepted:
        assert response.status_code == (201 if method == "POST" else 200)
        assert response.json()["polygon"]["coordinates"][0][0][0] == west
    else:
        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "El contorno se superpone con el sector «El bajo»."
        )
        assert api.get(units_url(scenario)).json() == before


def test_sectors_can_overlap_in_different_scenarios(
    api: TestClient, session: Session, scenario: Scenario, user: User
):
    alternative = Scenario(user_id=user.id, name="Alternativo", is_main=False)
    session.add(alternative)
    session.flush()

    for current in (scenario, alternative):
        response = api.post(
            units_url(current), json={"name": "Potrero", "polygon": SQUARE}
        )
        assert response.status_code == 201


def test_open_ring_is_rejected():
    open_ring = {
        "type": "Polygon",
        "coordinates": [SQUARE["coordinates"][0][:-1] + [[-68.0, -34.0]]],
    }

    with pytest.raises(ValueError):
        PolygonGeoJSON.model_validate(open_ring)


def test_delete_unit(api: TestClient, scenario: Scenario):
    unit = api.post(
        units_url(scenario), json={"name": "Potrero", "polygon": SQUARE}
    ).json()

    response = api.delete(f"/production-units/{unit['id']}")

    assert response.status_code == 204
    assert api.get(units_url(scenario)).json() == []


def test_other_users_scenario_is_not_found(api: TestClient, other_scenario: Scenario):
    assert api.get(units_url(other_scenario)).status_code == 404
    response = api.post(
        units_url(other_scenario), json={"name": "X", "polygon": SQUARE}
    )
    assert response.status_code == 404


def test_other_users_unit_is_not_found(
    api: TestClient, session: Session, other_scenario: Scenario
):
    unit = create_unit(
        session, other_scenario.id, "Ajeno", PolygonGeoJSON.model_validate(SQUARE)
    )
    url = f"/production-units/{unit.id}"

    assert api.put(url, json={"name": "Mío", "polygon": SQUARE}).status_code == 404
    assert api.delete(url).status_code == 404
