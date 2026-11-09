from datetime import date, timedelta

from sqlalchemy import exists, select
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


def years_text(years: list[int]) -> str:
    """[2026, 2027, 2028] → "2026, 2027 o 2028"."""
    *first, last = [str(year) for year in years]
    return f"{', '.join(first)} o {last}" if first else last


def create_scenario(
    session: Session,
    user_id: int,
    name: str,
    first_season_start_year: int,
    today: date,
) -> tuple[Scenario, Season]:
    """Crea el establecimiento junto con su primera campaña.

    El primer establecimiento del usuario queda como principal.
    """
    start_month = get_season_start_month(session)
    allowed = first_season_years(today, start_month)
    if first_season_start_year not in allowed:
        raise InvalidFirstSeasonYearError(
            f"El año de la primera campaña tiene que ser {years_text(allowed)}."
        )

    has_scenarios = session.scalar(select(exists().where(Scenario.user_id == user_id)))
    scenario = Scenario(user_id=user_id, name=name, is_main=not has_scenarios)
    session.add(scenario)
    session.flush()

    start, end = season_dates(first_season_start_year, start_month)
    season = Season(scenario_id=scenario.id, start_date=start, end_date=end)
    session.add(season)
    session.flush()
    return scenario, season


def list_scenarios(session: Session, user_id: int) -> list[Scenario]:
    """Establecimientos del usuario, ordenados por fecha de creación."""
    return list(
        session.scalars(
            select(Scenario)
            .where(Scenario.user_id == user_id)
            .order_by(Scenario.created_at, Scenario.id)
        )
    )


def get_user_scenario(
    session: Session, user_id: int, scenario_id: int
) -> Scenario | None:
    """El establecimiento, solo si es del usuario."""
    return session.scalar(
        select(Scenario).where(Scenario.id == scenario_id, Scenario.user_id == user_id)
    )


def list_seasons(session: Session, scenario_id: int) -> list[Season]:
    """Campañas del establecimiento, ordenadas por año."""
    return list(
        session.scalars(
            select(Season)
            .where(Season.scenario_id == scenario_id)
            .order_by(Season.start_date)
        )
    )


def current_season_id(seasons: list[Season], today: date) -> int | None:
    """La campaña que contiene a today o, si ninguna la contiene, la más cercana."""

    def distance(season: Season) -> int:
        if season.start_date <= today <= season.end_date:
            return 0
        return min(
            abs((season.start_date - today).days), abs((season.end_date - today).days)
        )

    return min(seasons, key=distance).id if seasons else None
