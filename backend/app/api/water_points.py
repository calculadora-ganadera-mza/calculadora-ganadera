from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.schemas.water_point import WaterPointInput, WaterPointRead
from app.services import water_points as service

router = APIRouter(tags=["water-points"])


@router.get("/production-units/{production_unit_id}/water-points")
def list_points(
    production_unit_id: int, session: SessionDep, user: CurrentUser
) -> list[WaterPointRead]:
    try:
        rows = service.list_user_points(session, user.id, production_unit_id)
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    return [WaterPointRead.model_validate(row) for row in rows]


@router.post("/production-units/{production_unit_id}/water-points", status_code=201)
def create_point(
    production_unit_id: int,
    data: WaterPointInput,
    session: SessionDep,
    user: CurrentUser,
) -> WaterPointRead:
    try:
        row = service.create_point(session, user.id, production_unit_id, data)
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    return WaterPointRead.model_validate(row)


@router.put("/water-points/{water_point_id}")
def update_point(
    water_point_id: int, data: WaterPointInput, session: SessionDep, user: CurrentUser
) -> WaterPointRead:
    try:
        row = service.update_point(session, user.id, water_point_id, data)
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    return WaterPointRead.model_validate(row)


@router.delete("/water-points/{water_point_id}", status_code=204)
def delete_point(water_point_id: int, session: SessionDep, user: CurrentUser) -> None:
    try:
        service.delete_point(session, user.id, water_point_id)
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
