from datetime import date, timedelta

from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import violated_constraint
from app.models import Scenario, Season, User
from app.schemas.scenario import SeasonRead
from app.services.parameters import select_parameter

# Años que se pueden elegir para la primera campaña: el actual y los siguientes
FIRST_SEASON_YEARS_AHEAD = 2


class InvalidFirstSeasonYearError(ValueError):
    """El año elegido para la primera campaña no está entre los permitidos."""


class SeasonExistsError(ValueError):
    """El establecimiento ya tiene una campaña para ese año."""


def season_dates(start_year: int, start_month: int) -> tuple[date, date]:
    """Inicio y fin de la campaña que arranca en start_month de start_year.

    La campaña dura un año: termina el día anterior al inicio de la siguiente.
    """
    start = date(start_year, start_month, 1)
    end = date(start_year + 1, start_month, 1) - timedelta(days=1)
    return start, end


def current_season_start_year(today: date, start_month: int) -> int:
    """Año en que arrancó la campaña que contiene a today.

    El "año actual" de la issue #8 se toma como el año en que empezó la campaña
    en curso: en marzo de 2027 sigue siendo 2026, porque esa campaña empezó en
    julio de 2026.
    """
    return today.year if today.month >= start_month else today.year - 1


def first_season_years(today: date, start_month: int) -> list[int]:
    """Años permitidos para la primera campaña: el actual y los dos siguientes."""
    current = current_season_start_year(today, start_month)
    return [current + offset for offset in range(FIRST_SEASON_YEARS_AHEAD + 1)]


def get_season_start_month(session: Session) -> int:
    value = session.scalars(select_parameter("season_start_month")).one()
    if value is None:
        raise ValueError("El parámetro season_start_month no tiene valor.")
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

    # Bloquea la fila del usuario para que dos altas concurrentes no choquen
    # con el índice único uq_scenario_main_per_user
    session.execute(select(User.id).where(User.id == user_id).with_for_update())
    has_scenarios = session.scalar(select(exists().where(Scenario.user_id == user_id)))
    scenario = Scenario(user_id=user_id, name=name, is_main=not has_scenarios)
    session.add(scenario)
    session.flush()

    start, end = season_dates(first_season_start_year, start_month)
    season = Season(scenario_id=scenario.id, start_date=start, end_date=end)
    session.add(season)
    session.flush()
    return scenario, season


def update_scenario(
    session: Session,
    scenario: Scenario,
    *,
    name: str | None = None,
    is_main: bool = False,
) -> Scenario:
    """Renombra un establecimiento o lo marca como principal.

    Al marcarlo como principal, el anterior del mismo usuario deja de serlo.
    Bloquea la fila del usuario para que dos cambios concurrentes no choquen
    con el índice único uq_scenario_main_per_user.
    """
    if name is not None:
        scenario.name = name
    if is_main and not scenario.is_main:
        session.execute(
            select(User.id).where(User.id == scenario.user_id).with_for_update()
        )
        session.execute(
            update(Scenario)
            .where(Scenario.user_id == scenario.user_id, Scenario.is_main.is_(True))
            .values(is_main=False)
        )
        scenario.is_main = True
    session.flush()
    return scenario


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


def get_user_season(session: Session, user_id: int, season_id: int) -> Season | None:
    """La campaña, solo si es de un establecimiento del usuario."""
    return session.scalar(
        select(Season)
        .join(Scenario)
        .where(Season.id == season_id, Scenario.user_id == user_id)
    )


def season_reads(seasons: list[Season], today: date) -> list[SeasonRead]:
    """Campañas en el formato de la API, con la actual marcada."""
    current_id = current_season_id(seasons, today)
    return [
        SeasonRead(
            id=season.id,
            start_year=season.start_date.year,
            start_date=season.start_date,
            end_date=season.end_date,
            rainfall_mm=season.rainfall_mm,
            is_current=season.id == current_id,
        )
        for season in seasons
    ]


def create_season(session: Session, scenario_id: int, start_year: int) -> Season:
    """Crea una campaña sin datos para el año pedido, si el establecimiento no la tiene.

    Cada pantalla decide qué años ofrece: Mi campo, solo los posteriores, y
    Seguimiento, solo los anteriores. Que no se cruce en fechas con otra
    campaña lo decide la restricción ex_season_no_overlap de la base, que vale
    aunque cambie el mes de inicio y aunque lleguen dos pedidos al mismo tiempo.
    """
    start, end = season_dates(start_year, get_season_start_month(session))
    season = Season(scenario_id=scenario_id, start_date=start, end_date=end)
    try:
        # El add y el flush van dentro del savepoint, para que el error quede
        # aislado en él
        with session.begin_nested():
            session.add(season)
            session.flush()
    except IntegrityError as err:
        if violated_constraint(err) != "ex_season_no_overlap":
            raise
        raise SeasonExistsError(
            "El establecimiento ya tiene una campaña para ese año."
        ) from err
    return season
