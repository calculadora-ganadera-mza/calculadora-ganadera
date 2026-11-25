from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.schemas.history import HistoryEntry
from app.services.history import unit_history
from app.services.production_units import get_user_unit

router = APIRouter(tags=["history"])


@router.get("/production-units/{production_unit_id}/history")
def get_unit_history(
    production_unit_id: int, session: SessionDep, user: CurrentUser
) -> list[HistoryEntry]:
    """Evolución del sector campaña a campaña."""
    unit = get_user_unit(session, user.id, production_unit_id)
    if unit is None:
        raise HTTPException(404, "Sector no encontrado.")
    return unit_history(session, unit)
