from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnimalCategory, ProductionUnit, Season, User
from app.models.enums import ProductionSystem, RangeCondition
from app.schemas.herd import HerdCategoryInput, HerdData
from app.services.herds import create_herd
from app.services.scenarios import create_scenario, create_season

TODAY = date(2026, 11, 5)

# Cuadrado de unos 900 m de lado en Mendoza
SQUARE_WKT = (
    "SRID=4326;POLYGON((-68.5 -33,-68.49 -33,-68.49 -32.99,-68.5 -32.99,-68.5 -33))"
)


def category(session: Session, code: str) -> AnimalCategory:
    return session.scalars(
        select(AnimalCategory).where(AnimalCategory.code == code)
    ).one()


def make_unit(session: Session, scenario_id: int) -> int:
    unit = ProductionUnit(
        scenario_id=scenario_id,
        name="Potrero",
        production_system=ProductionSystem.RAINFED,
        polygon=SQUARE_WKT,
    )
    session.add(unit)
    session.flush()
    return unit.id


def herd_data(session: Session, cows: int, bulls: int) -> HerdData:
    return HerdData(
        categories=[
            HerdCategoryInput(
                animal_category_id=category(session, "bull").id, quantity=bulls
            ),
            HerdCategoryInput(
                animal_category_id=category(session, "cow").id, quantity=cows
            ),
        ],
        range_condition=RangeCondition.GOOD,
        replacement_rate=0.2,
        weaning_rate=0.65,
        breeding_start=date(2026, 11, 1),
        breeding_end=date(2027, 1, 31),
    )


def test_history_has_one_entry_per_season_in_year_order(
    api: TestClient, session: Session, user: User
):
    scenario, current = create_scenario(session, user.id, "La Aguada", 2026, TODAY)
    unit_id = make_unit(session, scenario.id)
    past = create_season(session, scenario.id, 2025)
    past.rainfall_mm = 260
    current.rainfall_mm = 300
    create_herd(
        session, session.get(Season, current.id), unit_id, herd_data(session, 80, 3)
    )

    response = api.get(f"/production-units/{unit_id}/history")

    assert response.status_code == 200
    cow, bull = category(session, "cow"), category(session, "bull")
    # Las categorías salen en el orden de la tabla, no en el de la carga
    expected_categories = sorted(
        [
            {"animal_category_id": cow.id, "name": cow.name, "quantity": 80},
            {"animal_category_id": bull.id, "name": bull.name, "quantity": 3},
        ],
        key=lambda item: item["animal_category_id"],
    )
    assert response.json() == [
        {
            "season_id": past.id,
            "start_year": 2025,
            "categories": [],
            "replacement_rate": None,
            "weaning_rate": None,
            "rainfall_mm": 260,
        },
        {
            "season_id": current.id,
            "start_year": 2026,
            "categories": expected_categories,
            "replacement_rate": 0.2,
            "weaning_rate": 0.65,
            "rainfall_mm": 300,
        },
    ]


def test_history_only_has_the_herd_of_that_unit(
    api: TestClient, session: Session, user: User
):
    scenario, season = create_scenario(session, user.id, "La Aguada", 2026, TODAY)
    unit_id = make_unit(session, scenario.id)
    other_unit_id = make_unit(session, scenario.id)
    create_herd(
        session,
        session.get(Season, season.id),
        other_unit_id,
        herd_data(session, 50, 2),
    )

    entries = api.get(f"/production-units/{unit_id}/history").json()

    assert [entry["categories"] for entry in entries] == [[]]


@pytest.mark.parametrize("owner", ["other", "missing"])
def test_history_of_a_unit_that_is_not_yours_is_not_found(
    api: TestClient, session: Session, other_user: User, owner: str
):
    if owner == "other":
        scenario, _ = create_scenario(session, other_user.id, "Ajeno", 2026, TODAY)
        unit_id = make_unit(session, scenario.id)
    else:
        unit_id = 999_999

    response = api.get(f"/production-units/{unit_id}/history")

    assert response.status_code == 404
    assert response.json() == {"detail": "Sector no encontrado."}


def test_history_requires_login():
    from app.main import app

    assert TestClient(app).get("/production-units/1/history").status_code == 401
