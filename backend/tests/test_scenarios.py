from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dates import today
from app.main import app
from app.models import Scenario, Season, User
from app.schemas.scenario import ScenarioCreate
from app.services.scenarios import (
    InvalidFirstSeasonYearError,
    create_scenario,
    current_season_id,
    current_season_start_year,
    first_season_years,
    get_season_start_month,
    season_dates,
    years_text,
)

client = TestClient(app)

# 5 de noviembre de 2026: la campaña actual arrancó en julio de 2026
TODAY = date(2026, 11, 5)


# Fechas de las campañas


def test_season_goes_from_july_to_june():
    assert season_dates(2026, 7) == (date(2026, 7, 1), date(2027, 6, 30))


def test_season_starting_in_january_ends_in_december():
    assert season_dates(2026, 1) == (date(2026, 1, 1), date(2026, 12, 31))


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 7, 1), 2026),
        (date(2026, 11, 5), 2026),
        (date(2027, 3, 1), 2026),
        (date(2027, 6, 30), 2026),
    ],
)
def test_current_season_start_year(today: date, expected: int):
    assert current_season_start_year(today, 7) == expected


def test_first_season_years_are_current_and_two_next():
    assert first_season_years(TODAY, 7) == [2026, 2027, 2028]


def test_years_text():
    assert years_text([2026, 2027, 2028]) == "2026, 2027 o 2028"


def test_season_start_month_comes_from_parameter(session: Session):
    assert get_season_start_month(session) == 7


# Campaña actual


def season(id_: int, start_year: int) -> Season:
    start, end = season_dates(start_year, 7)
    return Season(id=id_, start_date=start, end_date=end)


def test_current_season_is_the_one_containing_today():
    seasons = [season(1, 2025), season(2, 2026), season(3, 2027)]

    assert current_season_id(seasons, TODAY) == 2


def test_current_season_is_the_closest_when_none_contains_today():
    seasons = [season(1, 2027), season(2, 2028)]

    assert current_season_id(seasons, TODAY) == 1


def test_current_season_without_seasons():
    assert current_season_id([], TODAY) is None


# Crear el establecimiento


def test_create_scenario_creates_its_first_season(session: Session, user: User):
    scenario, season = create_scenario(session, user.id, "La Aguada", 2027, TODAY)

    assert scenario.user_id == user.id
    assert scenario.name == "La Aguada"
    seasons = session.scalars(
        select(Season).where(Season.scenario_id == scenario.id)
    ).all()
    assert seasons == [season]
    assert (season.start_date, season.end_date) == (date(2027, 7, 1), date(2028, 6, 30))


def test_first_scenario_is_main_and_the_next_ones_are_not(session: Session, user: User):
    first, _ = create_scenario(session, user.id, "La Aguada", 2026, TODAY)
    second, _ = create_scenario(session, user.id, "El Puesto", 2026, TODAY)

    assert first.is_main is True
    assert second.is_main is False


def test_only_one_main_scenario_per_user(session: Session, user: User):
    create_scenario(session, user.id, "La Aguada", 2026, TODAY)

    with (
        pytest.raises(IntegrityError, match="uq_scenario_main_per_user"),
        session.begin_nested(),
    ):
        session.add(Scenario(user_id=user.id, name="Otro principal", is_main=True))


@pytest.mark.parametrize("year", [2025, 2029])
def test_create_scenario_rejects_year_out_of_range(
    session: Session, user: User, year: int
):
    with pytest.raises(
        InvalidFirstSeasonYearError, match="tiene que ser 2026, 2027 o 2028"
    ):
        create_scenario(session, user.id, "La Aguada", year, TODAY)


def test_scenario_name_is_trimmed():
    data = ScenarioCreate(name="  La Aguada  ", first_season_start_year=2026)

    assert data.name == "La Aguada"


@pytest.mark.parametrize("name", ["   ", "x" * 101])
def test_scenario_name_must_have_1_to_100_characters(name: str):
    with pytest.raises(ValidationError):
        ScenarioCreate(name=name, first_season_start_year=2026)


# Rutas


def test_register_scenario(api: TestClient):
    year = current_season_start_year(today(), 7)

    response = api.post(
        "/scenarios", json={"name": " La Aguada ", "first_season_start_year": year}
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "name": "La Aguada", "is_main": True}


def test_register_scenario_rejects_year_out_of_range(api: TestClient):
    year = current_season_start_year(today(), 7) + 3

    response = api.post(
        "/scenarios", json={"name": "La Aguada", "first_season_start_year": year}
    )

    assert response.status_code == 422
    assert "tiene que ser" in response.json()["detail"]


def test_register_scenario_rejects_blank_name(api: TestClient):
    year = current_season_start_year(today(), 7)

    response = api.post(
        "/scenarios", json={"name": "  ", "first_season_start_year": year}
    )

    assert response.status_code == 422


def test_list_scenarios_shows_only_the_users_own_in_creation_order(
    api: TestClient, session: Session, user: User, other_user: User
):
    create_scenario(session, other_user.id, "Ajeno", 2026, TODAY)
    create_scenario(session, user.id, "La Aguada", 2026, TODAY)
    create_scenario(session, user.id, "El Puesto", 2026, TODAY)

    response = api.get("/scenarios")

    assert response.status_code == 200
    assert [(s["name"], s["is_main"]) for s in response.json()] == [
        ("La Aguada", True),
        ("El Puesto", False),
    ]


def test_list_seasons_of_a_scenario(api: TestClient, session: Session, user: User):
    year = current_season_start_year(today(), 7)
    scenario, _ = create_scenario(session, user.id, "La Aguada", year, today())

    response = api.get(f"/scenarios/{scenario.id}/seasons")

    assert response.status_code == 200
    [season] = response.json()
    assert season["start_year"] == year
    assert season["start_date"] == f"{year}-07-01"
    assert season["end_date"] == f"{year + 1}-06-30"
    assert season["rainfall_mm"] is None
    assert season["is_current"] is True


def test_list_seasons_of_another_users_scenario_is_not_found(
    api: TestClient, session: Session, other_user: User
):
    scenario, _ = create_scenario(session, other_user.id, "Ajeno", 2026, TODAY)

    response = api.get(f"/scenarios/{scenario.id}/seasons")

    assert response.status_code == 404
    assert response.json() == {"detail": "Establecimiento no encontrado."}


def test_first_season_years_endpoint(api: TestClient):
    response = api.get("/scenarios/first-season-years")

    assert response.status_code == 200
    options = response.json()
    current = current_season_start_year(today(), 7)
    assert [option["start_year"] for option in options] == [
        current,
        current + 1,
        current + 2,
    ]
    assert options[0]["start_date"] == f"{current}-07-01"
    assert options[0]["end_date"] == f"{current + 1}-06-30"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/scenarios"),
        ("post", "/scenarios"),
        ("get", "/scenarios/1/seasons"),
        ("get", "/scenarios/first-season-years"),
    ],
)
def test_routes_require_login(method: str, path: str):
    response = client.request(
        method, path, json={"name": "x", "first_season_start_year": 2026}
    )

    assert response.status_code == 401
