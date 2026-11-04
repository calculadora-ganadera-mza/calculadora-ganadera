from fastapi import FastAPI

from app.api import health

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
