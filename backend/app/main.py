from fastapi import FastAPI

from app.api import health, scenarios

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
app.include_router(scenarios.router)
