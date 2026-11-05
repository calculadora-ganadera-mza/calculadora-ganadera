from datetime import date

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.scenario import SeasonYearOption
from app.services.scenarios import (
    first_season_years,
    get_season_start_month,
    season_dates,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


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
