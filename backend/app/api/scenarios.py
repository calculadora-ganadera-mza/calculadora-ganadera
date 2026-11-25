from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, OwnedScenario, SessionDep
from app.core.dates import today
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioRead,
    ScenarioUpdate,
    SeasonCreate,
    SeasonRead,
    SeasonYearOption,
)
from app.services.scenarios import (
    InvalidFirstSeasonYearError,
    SeasonExistsError,
    create_scenario,
    create_season,
    first_season_years,
    get_season_start_month,
    list_scenarios,
    list_seasons,
    season_dates,
    season_reads,
    update_scenario,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# Ruta agregada para que el formulario no tenga que calcular los años.
@router.get("/first-season-years")
def list_first_season_years(
    session: SessionDep, user: CurrentUser
) -> list[SeasonYearOption]:
    """Años que se pueden elegir para la primera campaña de un establecimiento."""
    start_month = get_season_start_month(session)
    options = []
    for year in first_season_years(today(), start_month):
        start, end = season_dates(year, start_month)
        options.append(
            SeasonYearOption(start_year=year, start_date=start, end_date=end)
        )
    return options


@router.get("")
def list_user_scenarios(session: SessionDep, user: CurrentUser) -> list[ScenarioRead]:
    """Establecimientos del usuario, ordenados por fecha de creación."""
    return [
        ScenarioRead.model_validate(scenario)
        for scenario in list_scenarios(session, user.id)
    ]


@router.post("", status_code=201)
def register_scenario(
    data: ScenarioCreate, session: SessionDep, user: CurrentUser
) -> ScenarioRead:
    """Registra un establecimiento del usuario, con su primera campaña."""
    try:
        scenario, _ = create_scenario(
            session, user.id, data.name, data.first_season_start_year, today()
        )
    except InvalidFirstSeasonYearError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return ScenarioRead.model_validate(scenario)


@router.patch("/{scenario_id}")
def edit_scenario(
    data: ScenarioUpdate, scenario: OwnedScenario, session: SessionDep
) -> ScenarioRead:
    """Renombra un establecimiento o lo marca como principal."""
    updated = update_scenario(
        session, scenario, name=data.name, is_main=bool(data.is_main)
    )
    session.commit()
    return ScenarioRead.model_validate(updated)


@router.get("/{scenario_id}/seasons")
def list_scenario_seasons(
    scenario: OwnedScenario, session: SessionDep
) -> list[SeasonRead]:
    """Campañas del establecimiento, ordenadas por año."""
    return season_reads(list_seasons(session, scenario.id), today())


@router.post("/{scenario_id}/seasons", status_code=201)
def add_season(
    data: SeasonCreate, scenario: OwnedScenario, session: SessionDep
) -> SeasonRead:
    """Crea una campaña sin datos para un año que el establecimiento no tiene."""
    try:
        season = create_season(session, scenario.id, data.start_year)
    except SeasonExistsError as err:
        raise HTTPException(409, str(err)) from err
    session.commit()
    # is_current depende de las demás campañas del establecimiento
    reads = season_reads(list_seasons(session, scenario.id), today())
    return next(read for read in reads if read.id == season.id)
