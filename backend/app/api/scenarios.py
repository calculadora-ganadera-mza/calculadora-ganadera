from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.jwt import get_current_user
from app.models.user import User
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioRead,
    SeasonRead,
    SeasonYearOption,
)
from app.services.scenarios import (
    InvalidFirstSeasonYearError,
    create_scenario,
    first_season_years,
    get_season_start_month,
    list_scenarios,
    season_dates,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/first-season-years")
def list_first_season_years(session: SessionDep) -> list[SeasonYearOption]:
    """Años que se pueden elegir para la primera campaña de un establecimiento."""
    start_month = get_season_start_month(session)
    options = []
    for year in first_season_years(date.today(), start_month):
        start, end = season_dates(year, start_month)
        options.append(
            SeasonYearOption(start_year=year, start_date=start, end_date=end)
        )
    return options


@router.post("", status_code=201)
def register_scenario(
    data: ScenarioCreate, session: SessionDep, user: CurrentUser
) -> ScenarioRead:
    """Registra un establecimiento del usuario, con su primera campaña."""
    try:
        scenario, season = create_scenario(
            session, user.id, data.name, data.first_season_year, date.today()
        )
    except InvalidFirstSeasonYearError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return ScenarioRead(
        id=scenario.id, name=scenario.name, seasons=[SeasonRead.model_validate(season)]
    )


@router.get("")
def list_user_scenarios(session: SessionDep, user: CurrentUser) -> list[ScenarioRead]:
    """Establecimientos del usuario, cada uno con sus campañas."""
    return [
        ScenarioRead(
            id=scenario.id,
            name=scenario.name,
            seasons=[SeasonRead.model_validate(season) for season in seasons],
        )
        for scenario, seasons in list_scenarios(session, user.id)
    ]
