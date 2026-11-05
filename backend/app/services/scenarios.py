from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Parameter, Scenario, Season

# Años que se pueden elegir para la primera campaña: el actual y los siguientes
FIRST_SEASON_YEARS_AHEAD = 2


class InvalidFirstSeasonYearError(ValueError):
    """El año elegido para la primera campaña no está entre los permitidos."""


def season_dates(start_year: int, start_month: int) -> tuple[date, date]:
    """Inicio y fin de la campaña que arranca en start_month de start_year.

    La campaña dura un año: termina el día anterior al inicio de la siguiente.
    """
    start = date(start_year, start_month, 1)
    end = date(start_year + 1, start_month, 1) - timedelta(days=1)
    return start, end


def current_season_start_year(today: date, start_month: int) -> int:
    """Año en que arrancó la campaña que contiene a today."""
    return today.year if today.month >= start_month else today.year - 1


def first_season_years(today: date, start_month: int) -> list[int]:
    """Años permitidos para la primera campaña: el actual y los dos siguientes."""
    current = current_season_start_year(today, start_month)
    return [current + offset for offset in range(FIRST_SEASON_YEARS_AHEAD + 1)]


def get_season_start_month(session: Session) -> int:
    value = session.scalars(
        select(Parameter.value).where(Parameter.key == "season_start_month")
    ).one()
    return int(value)


def create_scenario(
    session: Session, user_id: int, name: str, first_season_year: int, today: date
) -> tuple[Scenario, Season]:
    """Crea el establecimiento junto con su primera campaña."""
    start_month = get_season_start_month(session)
    allowed = first_season_years(today, start_month)
    if first_season_year not in allowed:
        raise InvalidFirstSeasonYearError(
            f"El año de la primera campaña tiene que ser uno de {allowed}."
        )

    scenario = Scenario(user_id=user_id, name=name)
    session.add(scenario)
    session.flush()

    start, end = season_dates(first_season_year, start_month)
    season = Season(scenario_id=scenario.id, start_date=start, end_date=end)
    session.add(season)
    session.flush()
    return scenario, season
