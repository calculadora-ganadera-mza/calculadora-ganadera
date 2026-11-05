from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models import Season, User
from app.schemas.scenario import ScenarioCreate
from app.services.scenarios import (
    InvalidFirstSeasonYearError,
    create_scenario,
    current_season_start_year,
    first_season_years,
    get_season_start_month,
    season_dates,
)

client = TestClient(app)

# 5 de noviembre de 2026: la campaña actual arrancó en julio de 2026
TODAY = date(2026, 11, 5)


@pytest.fixture
def user(session: Session) -> User:
    user = User(name="Prueba", email="prueba@example.com", password_hash="x")
    session.add(user)
    session.flush()
    return user


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


def test_season_start_month_comes_from_parameter(session: Session):
    assert get_season_start_month(session) == 7


def test_create_scenario_creates_its_first_season(session: Session, user: User):
    scenario, season = create_scenario(session, user.id, "La Aguada", 2027, TODAY)

    assert scenario.user_id == user.id
    assert scenario.name == "La Aguada"
    seasons = session.scalars(
        select(Season).where(Season.scenario_id == scenario.id)
    ).all()
    assert seasons == [season]
    assert (season.start_date, season.end_date) == (date(2027, 7, 1), date(2028, 6, 30))


@pytest.mark.parametrize("year", [2025, 2029])
def test_create_scenario_rejects_year_out_of_range(
    session: Session, user: User, year: int
):
    with pytest.raises(InvalidFirstSeasonYearError):
        create_scenario(session, user.id, "La Aguada", year, TODAY)


def test_scenario_name_is_trimmed():
    data = ScenarioCreate(name="  La Aguada  ", first_season_year=2026)

    assert data.name == "La Aguada"


def test_scenario_name_cannot_be_blank():
    with pytest.raises(ValidationError):
        ScenarioCreate(name="   ", first_season_year=2026)


def test_first_season_years_endpoint():
    response = client.get("/scenarios/first-season-years")

    assert response.status_code == 200
    options = response.json()
    current = current_season_start_year(date.today(), 7)
    assert [option["start_year"] for option in options] == [
        current,
        current + 1,
        current + 2,
    ]
    assert options[0]["start_date"] == f"{current}-07-01"
    assert options[0]["end_date"] == f"{current + 1}-06-30"
