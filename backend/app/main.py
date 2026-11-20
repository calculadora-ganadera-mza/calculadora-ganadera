from fastapi import FastAPI

from app.api import (
    auth,
    carrying_capacity,
    health,
    herds,
    production_units,
    reference_data,
    scenarios,
    water_points,
)

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(production_units.router)
app.include_router(scenarios.router)
app.include_router(water_points.router)
app.include_router(herds.router)
app.include_router(carrying_capacity.router)
app.include_router(reference_data.router)
