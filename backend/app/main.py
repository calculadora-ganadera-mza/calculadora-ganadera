from fastapi import FastAPI

from app.api import auth, health, herds, production_units, scenarios

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(production_units.router)
app.include_router(scenarios.router)
app.include_router(herds.router)
