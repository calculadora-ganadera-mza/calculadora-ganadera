from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, OwnedScenario, SessionDep
from app.schemas.water_point import (
    ScenarioWaterPointRead,
    WaterPointInput,
    WaterPointRead,
)
from app.services import water_points as service

router = APIRouter(tags=["water-points"])


@router.get("/production-units/{production_unit_id}/water-points")
def list_points(
    production_unit_id: int, session: SessionDep, user: CurrentUser
) -> list[WaterPointRead]:
    try:
        rows = service.list_user_points(session, user.id, production_unit_id)
    except service.InvalidWaterPointError as err:
        raise HTTPException(422, str(err)) from err
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
    except service.InvalidWaterPointError as err:
        raise HTTPException(422, str(err)) from err
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    return WaterPointRead.model_validate(row)


@router.put("/water-points/{water_point_id}")
def update_point(
    water_point_id: int, data: WaterPointInput, session: SessionDep, user: CurrentUser
) -> WaterPointRead:
    try:
        row = service.update_point(session, user.id, water_point_id, data)
    except service.InvalidWaterPointError as err:
        raise HTTPException(422, str(err)) from err
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    return WaterPointRead.model_validate(row)


@router.delete("/water-points/{water_point_id}", status_code=204)
def delete_point(water_point_id: int, session: SessionDep, user: CurrentUser) -> None:
    try:
        service.delete_point(session, user.id, water_point_id)
    except service.InvalidWaterPointError as err:
        raise HTTPException(422, str(err)) from err
    except service.WaterPointNotFoundError as err:
        raise HTTPException(404, str(err)) from err


@router.get("/scenarios/{scenario_id}/water-points")
def list_scenario_points(
    scenario: OwnedScenario, session: SessionDep
) -> list[ScenarioWaterPointRead]:
    return [
        ScenarioWaterPointRead.model_validate(row)
        for row in service.read_points(session, scenario_id=scenario.id)
    ]
