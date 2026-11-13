from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.core.dates import today
from app.models import Season
from app.schemas.animal_category import AnimalCategoryRead
from app.schemas.herd import HerdCreate, HerdData, HerdRead
from app.schemas.scenario import SeasonRead, SeasonUpdate
from app.services.herds import (
    HerdExistsError,
    InvalidHerdError,
    UnitNotFoundError,
    create_herd,
    get_user_herd,
    herd_read,
    list_animal_categories,
    list_herds,
    update_herd,
)
from app.services.scenarios import get_user_season, list_seasons, season_reads

router = APIRouter()


def owned_season(session: SessionDep, user: CurrentUser, season_id: int) -> Season:
    """La campaña, solo si es del usuario; si no, 404."""
    season = get_user_season(session, user.id, season_id)
    if season is None:
        raise HTTPException(404, "Campaña no encontrada.")
    return season


@router.get("/animal-categories", tags=["reference-data"])
def list_categories(session: SessionDep, user: CurrentUser) -> list[AnimalCategoryRead]:
    """Categorías de animales, para el formulario del rodeo."""
    return [
        AnimalCategoryRead.model_validate(category)
        for category in list_animal_categories(session)
    ]


@router.patch("/seasons/{season_id}", tags=["seasons"])
def update_season_rainfall(
    season_id: int, data: SeasonUpdate, session: SessionDep, user: CurrentUser
) -> SeasonRead:
    """Cambia la lluvia de la campaña anterior; None la elimina."""
    season = owned_season(session, user, season_id)
    season.rainfall_mm = data.rainfall_mm
    session.commit()
    # is_current depende de las demás campañas del establecimiento
    reads = season_reads(list_seasons(session, season.scenario_id), today())
    return next(read for read in reads if read.id == season.id)


@router.get("/seasons/{season_id}/herds", tags=["herds"])
def list_season_herds(
    season_id: int, session: SessionDep, user: CurrentUser
) -> list[HerdRead]:
    """Rodeos de la campaña, uno por sector que ya tiene datos."""
    season = owned_season(session, user, season_id)
    return [herd_read(session, herd) for herd in list_herds(session, season.id)]


@router.post("/seasons/{season_id}/herds", status_code=201, tags=["herds"])
def register_herd(
    season_id: int, data: HerdCreate, session: SessionDep, user: CurrentUser
) -> HerdRead:
    """Registra el rodeo de un sector en la campaña."""
    season = owned_season(session, user, season_id)
    try:
        herd = create_herd(session, season, data.production_unit_id, data)
    except InvalidHerdError as err:
        raise HTTPException(422, str(err)) from err
    except UnitNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    except HerdExistsError as err:
        raise HTTPException(409, str(err)) from err
    session.commit()
    return herd_read(session, herd)


@router.put("/herds/{herd_id}", tags=["herds"])
def replace_herd(
    herd_id: int, data: HerdData, session: SessionDep, user: CurrentUser
) -> HerdRead:
    """Reemplaza los datos del rodeo."""
    herd = get_user_herd(session, user.id, herd_id)
    if herd is None:
        raise HTTPException(404, "Rodeo no encontrado.")
    try:
        update_herd(session, herd, data)
    except InvalidHerdError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return herd_read(session, herd)
