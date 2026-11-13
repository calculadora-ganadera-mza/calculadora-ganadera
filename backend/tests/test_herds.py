from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnimalCategory, ProductionUnit, Season, User
from app.models.enums import ProductionSystem, RangeCondition
from app.schemas.herd import HerdCategoryInput, HerdData
from app.services.herds import InvalidHerdError, check_herd_rules, create_herd
from app.services.scenarios import create_scenario

TODAY = date(2026, 11, 5)

# Cuadrado de unos 900 m de lado en Mendoza
SQUARE_WKT = (
    "SRID=4326;POLYGON((-68.5 -33,-68.49 -33,-68.49 -32.99,-68.5 -32.99,-68.5 -33))"
)


def category_id(session: Session, code: str) -> int:
    return session.scalars(
        select(AnimalCategory.id).where(AnimalCategory.code == code)
    ).one()


def make_unit(session: Session, scenario_id: int, name: str = "Potrero") -> int:
    unit = ProductionUnit(
        scenario_id=scenario_id,
        name=name,
        production_system=ProductionSystem.RAINFED,
        polygon=SQUARE_WKT,
    )
    session.add(unit)
    session.flush()
    return unit.id


@pytest.fixture
def setup(session: Session, user: User) -> dict:
    """Establecimiento del usuario con su campaña y un sector."""
    scenario, season = create_scenario(session, user.id, "La Aguada", 2026, TODAY)
    return {
        "season": season,
        "unit_id": make_unit(session, scenario.id),
        "cow": category_id(session, "cow"),
        "bull": category_id(session, "bull"),
        "calf": category_id(session, "calf"),
    }


def herd_json(setup: dict, **changes) -> dict:
    """Rodeo completo con 100 vacas y 4 toros."""
    data = {
        "production_unit_id": setup["unit_id"],
        "categories": [
            {"animal_category_id": setup["cow"], "quantity": 100},
            {"animal_category_id": setup["bull"], "quantity": 4},
        ],
        "range_condition": "good",
        "replacement_rate": 0.2,
        "weaning_rate": 0.6,
        "early_weaning": True,
        "supplemented": False,
        "breeding_start": "2026-11-01",
        "breeding_end": "2027-01-31",
    }
    data.update(changes)
    return data


# Reglas del rodeo, sin base de datos

CODES = {1: "cow", 2: "bull", 4: "calf"}


def rules_data(**changes) -> HerdData:
    data = {
        "categories": [HerdCategoryInput(animal_category_id=2, quantity=3)],
        "range_condition": RangeCondition.GOOD,
    }
    data.update(changes)
    return HerdData(**data)


def test_herd_without_cows_does_not_need_rates_or_breeding():
    check_herd_rules(rules_data(), CODES)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"categories": [HerdCategoryInput(animal_category_id=1, quantity=10)]},
            "Si hay vacas",
        ),
        (
            {"categories": [HerdCategoryInput(animal_category_id=4, quantity=10)]},
            "terneros",
        ),
        (
            {
                "categories": [
                    HerdCategoryInput(animal_category_id=2, quantity=1),
                    HerdCategoryInput(animal_category_id=2, quantity=2),
                ]
            },
            "repetidas",
        ),
        (
            {"categories": [HerdCategoryInput(animal_category_id=99, quantity=1)]},
            "no existe",
        ),
        ({"breeding_start": date(2026, 11, 1)}, "inicio y fin"),
        (
            {"breeding_start": date(2027, 1, 1), "breeding_end": date(2026, 12, 1)},
            "posterior",
        ),
    ],
)
def test_herd_rules(changes: dict, message: str):
    with pytest.raises(InvalidHerdError, match=message):
        check_herd_rules(rules_data(**changes), CODES)


def test_zero_cows_does_not_count_as_having_cows():
    data = rules_data(categories=[HerdCategoryInput(animal_category_id=1, quantity=0)])

    check_herd_rules(data, CODES)


# Rutas


def test_list_animal_categories(api: TestClient):
    response = api.get("/animal-categories")

    assert response.status_code == 200
    codes = [category["code"] for category in response.json()]
    assert {"cow", "bull", "heifer", "calf", "steer"} <= set(codes)


def test_register_herd_and_list_it(api: TestClient, setup: dict):
    season_id = setup["season"].id

    response = api.post(f"/seasons/{season_id}/herds", json=herd_json(setup))

    assert response.status_code == 201
    herd = response.json()
    assert herd["production_unit_id"] == setup["unit_id"]
    assert herd["early_weaning"] is True
    assert herd["supplemented"] is False
    assert herd["breeding_end"] == "2027-01-31"
    assert sorted(
        (c["animal_category_id"], c["quantity"]) for c in herd["categories"]
    ) == sorted([(setup["cow"], 100), (setup["bull"], 4)])

    listed = api.get(f"/seasons/{season_id}/herds").json()
    assert [h["id"] for h in listed] == [herd["id"]]


def test_register_herd_twice_for_the_same_unit_is_a_conflict(
    api: TestClient, setup: dict
):
    season_id = setup["season"].id
    api.post(f"/seasons/{season_id}/herds", json=herd_json(setup))

    response = api.post(f"/seasons/{season_id}/herds", json=herd_json(setup))

    assert response.status_code == 409
    assert response.json() == {"detail": "El sector ya tiene un rodeo en esa campaña."}


def test_register_herd_with_cows_and_without_breeding_is_rejected(
    api: TestClient, setup: dict
):
    response = api.post(
        f"/seasons/{setup['season'].id}/herds",
        json=herd_json(setup, breeding_start=None, breeding_end=None),
    )

    assert response.status_code == 422
    assert "Si hay vacas" in response.json()["detail"]


def test_register_herd_with_calves_is_rejected(api: TestClient, setup: dict):
    data = herd_json(setup)
    data["categories"].append({"animal_category_id": setup["calf"], "quantity": 50})

    response = api.post(f"/seasons/{setup['season'].id}/herds", json=data)

    assert response.status_code == 422
    assert "terneros" in response.json()["detail"]


def test_register_herd_for_a_unit_of_another_scenario_is_not_found(
    api: TestClient, session: Session, setup: dict, user: User
):
    other_scenario, _ = create_scenario(session, user.id, "El Puesto", 2026, TODAY)
    other_unit = make_unit(session, other_scenario.id)

    response = api.post(
        f"/seasons/{setup['season'].id}/herds",
        json=herd_json(setup, production_unit_id=other_unit),
    )

    assert response.status_code == 404


def test_update_herd_replaces_its_data(api: TestClient, setup: dict):
    season_id = setup["season"].id
    herd = api.post(f"/seasons/{season_id}/herds", json=herd_json(setup)).json()
    data = herd_json(
        setup,
        categories=[{"animal_category_id": setup["bull"], "quantity": 2}],
        range_condition="fair",
        early_weaning=False,
        supplemented=True,
    )
    del data["production_unit_id"]

    response = api.put(f"/herds/{herd['id']}", json=data)

    assert response.status_code == 200
    updated = response.json()
    assert updated["range_condition"] == "fair"
    assert updated["supplemented"] is True
    assert updated["categories"] == [
        {"animal_category_id": setup["bull"], "quantity": 2}
    ]


def test_update_season_rainfall(api: TestClient, setup: dict):
    season_id = setup["season"].id

    response = api.patch(f"/seasons/{season_id}", json={"rainfall_mm": 280})

    assert response.status_code == 200
    assert response.json()["rainfall_mm"] == 280
    assert (
        api.patch(f"/seasons/{season_id}", json={"rainfall_mm": None}).json()[
            "rainfall_mm"
        ]
        is None
    )


def test_negative_rainfall_is_rejected(api: TestClient, setup: dict):
    response = api.patch(f"/seasons/{setup['season'].id}", json={"rainfall_mm": -1})

    assert response.status_code == 422


def test_another_users_season_and_herd_are_not_found(
    api: TestClient, session: Session, other_user: User
):
    scenario, season = create_scenario(session, other_user.id, "Ajeno", 2026, TODAY)
    unit_id = make_unit(session, scenario.id)
    bull = category_id(session, "bull")
    data = HerdData(
        categories=[HerdCategoryInput(animal_category_id=bull, quantity=1)],
        range_condition=RangeCondition.GOOD,
    )
    herd = create_herd(session, session.get(Season, season.id), unit_id, data)

    assert api.get(f"/seasons/{season.id}/herds").status_code == 404
    assert (
        api.patch(f"/seasons/{season.id}", json={"rainfall_mm": 1}).status_code == 404
    )
    put = api.put(f"/herds/{herd.id}", json=data.model_dump(mode="json"))
    assert put.status_code == 404
    assert put.json() == {"detail": "Rodeo no encontrado."}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/animal-categories"),
        ("patch", "/seasons/1"),
        ("get", "/seasons/1/herds"),
        ("post", "/seasons/1/herds"),
        ("put", "/herds/1"),
    ],
)
def test_routes_require_login(method: str, path: str):
    from app.main import app

    response = TestClient(app).request(method, path, json={})

    assert response.status_code == 401
