from fastapi import FastAPI

from app.api import (
    auth,
    carrying_capacity,
    health,
    herds,
    history,
    production_units,
    reference_data,
    scenarios,
    water_points,
)
from app.core.exception_handler import register_exception_handlers

app = FastAPI(title="Calculadora Ganadera")
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(production_units.router)
app.include_router(scenarios.router)
app.include_router(water_points.router)
app.include_router(herds.router)
app.include_router(history.router)
app.include_router(carrying_capacity.router)
app.include_router(reference_data.router)
