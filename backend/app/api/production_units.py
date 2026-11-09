from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, OwnedScenario, SessionDep
from app.schemas.production_unit import ProductionUnitInput, ProductionUnitRead
from app.services.production_units import (
    InvalidPolygonError,
    create_unit,
    get_user_unit,
    list_units,
    read_unit,
    update_unit,
)

router = APIRouter(tags=["production-units"])


@router.get("/scenarios/{scenario_id}/production-units")
def list_scenario_units(
    scenario: OwnedScenario, session: SessionDep
) -> list[ProductionUnitRead]:
    """Sectores del establecimiento, ordenados por fecha de creación."""
    return [
        ProductionUnitRead.model_validate(row)
        for row in list_units(session, scenario.id)
    ]


@router.post("/scenarios/{scenario_id}/production-units", status_code=201)
def draw_unit(
    data: ProductionUnitInput, scenario: OwnedScenario, session: SessionDep
) -> ProductionUnitRead:
    """Dibuja un sector en el establecimiento."""
    try:
        unit = create_unit(session, scenario.id, data.name, data.polygon)
    except InvalidPolygonError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return ProductionUnitRead.model_validate(read_unit(session, unit.id))


@router.put("/production-units/{production_unit_id}")
def edit_unit(
    production_unit_id: int,
    data: ProductionUnitInput,
    session: SessionDep,
    user: CurrentUser,
) -> ProductionUnitRead:
    """Cambia el nombre y el contorno del sector."""
    unit = get_user_unit(session, user.id, production_unit_id)
    if unit is None:
        raise HTTPException(404, "Sector no encontrado.")
    try:
        update_unit(session, unit, data.name, data.polygon)
    except InvalidPolygonError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return ProductionUnitRead.model_validate(read_unit(session, unit.id))


@router.delete("/production-units/{production_unit_id}", status_code=204)
def remove_unit(
    production_unit_id: int, session: SessionDep, user: CurrentUser
) -> None:
    """Elimina el sector. La base de datos borra tambien sus aguadas y rodeos."""
    unit = get_user_unit(session, user.id, production_unit_id)
    if unit is None:
        raise HTTPException(404, "Sector no encontrado.")
    session.delete(unit)
    session.commit()
