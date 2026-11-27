from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.calculators.carrying_capacity import NotCalculableError
from app.schemas.carrying_capacity import (
    CarryingCapacityCalculationCreate,
    CarryingCapacityCalculationRead,
    CarryingCapacityCalculationSummaryRead,
    CarryingCapacityInput,
    CarryingCapacityResult,
)
from app.services import carrying_capacity as service
from app.services.carrying_capacity import (
    CalculationNotFoundError,
    SeasonNotFoundError,
    UnsupportedSeasonUpdateError,
)
from app.services.herds import InvalidHerdError, UnitNotFoundError

router = APIRouter(tags=["carrying-capacity"])


@router.post("/production-units/{production_unit_id}/carrying-capacity")
def calculate(
    production_unit_id: int,
    data: CarryingCapacityInput,
    session: SessionDep,
    user: CurrentUser,
) -> CarryingCapacityResult:
    try:
        return service.calculate(session, user.id, production_unit_id, data)
    except UnitNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    except (InvalidHerdError, NotCalculableError) as err:
        raise HTTPException(422, str(err)) from err


@router.get("/carrying-capacity-calculations")
def list_user_calculations(
    session: SessionDep,
    user: CurrentUser,
) -> list[CarryingCapacityCalculationSummaryRead]:
    """Historial liviano de todos los cálculos guardados del usuario."""
    return service.list_user_calculations(session, user.id)


@router.get("/production-units/{production_unit_id}/carrying-capacity-calculations")
def list_calculations(
    production_unit_id: int,
    session: SessionDep,
    user: CurrentUser,
    season_id: int | None = None,
) -> list[CarryingCapacityCalculationRead]:
    """Cálculos guardados del sector, del más reciente al más antiguo."""
    try:
        return service.list_calculations(
            session, user.id, production_unit_id, season_id=season_id
        )
    except UnitNotFoundError as err:
        raise HTTPException(404, str(err)) from err


@router.post(
    "/production-units/{production_unit_id}/carrying-capacity-calculations",
    status_code=201,
)
def save_calculation(
    production_unit_id: int,
    data: CarryingCapacityCalculationCreate,
    session: SessionDep,
    user: CurrentUser,
) -> CarryingCapacityCalculationRead:
    """Calcula con los datos recibidos y guarda el resultado o la simulación."""
    try:
        return service.save_calculation(session, user.id, production_unit_id, data)
    except (UnitNotFoundError, SeasonNotFoundError) as err:
        raise HTTPException(404, str(err)) from err
    except (InvalidHerdError, NotCalculableError, UnsupportedSeasonUpdateError) as err:
        raise HTTPException(422, str(err)) from err


@router.get("/carrying-capacity-calculations/{calculation_id}")
def get_calculation(
    calculation_id: int,
    session: SessionDep,
    user: CurrentUser,
) -> CarryingCapacityCalculationRead:
    """Devuelve un cálculo guardado tal como fue registrado."""
    try:
        return service.get_user_calculation(session, user.id, calculation_id)
    except CalculationNotFoundError as err:
        raise HTTPException(404, str(err)) from err


@router.delete("/carrying-capacity-calculations/{calculation_id}", status_code=204)
def delete_calculation(
    calculation_id: int,
    session: SessionDep,
    user: CurrentUser,
) -> None:
    """Elimina un cálculo guardado."""
    try:
        service.delete_calculation(session, user.id, calculation_id)
    except CalculationNotFoundError as err:
        raise HTTPException(404, str(err)) from err
