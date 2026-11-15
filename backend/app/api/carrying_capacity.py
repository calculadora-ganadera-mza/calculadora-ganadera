from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.calculators.carrying_capacity import NotCalculableError
from app.schemas.carrying_capacity import CarryingCapacityInput, CarryingCapacityResult
from app.services import carrying_capacity as service
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
