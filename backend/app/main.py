from fastapi import FastAPI

from app.api import auth, health, scenarios

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(scenarios.router)
