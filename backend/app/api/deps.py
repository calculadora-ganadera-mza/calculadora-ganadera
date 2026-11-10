from typing import Annotated

from fastapi import Depends, HTTPException

# SessionDep se define en core/db.py porque core/jwt.py también lo usa, y core
# no depende de api. Se importa en este módulo para que las rutas tomen todas
# las dependencias de deps.
from app.core.db import SessionDep
from app.core.jwt import get_current_user
from app.models import Scenario, User
from app.services.scenarios import get_user_scenario

CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_scenario(
    scenario_id: int, session: SessionDep, user: CurrentUser
) -> Scenario:
    """El establecimiento de la ruta, solo si es del usuario; si no, 404."""
    scenario = get_user_scenario(session, user.id, scenario_id)
    if scenario is None:
        raise HTTPException(404, "Establecimiento no encontrado.")
    return scenario


OwnedScenario = Annotated[Scenario, Depends(get_owned_scenario)]
