from fastapi import FastAPI

from app.api import auth, health

app = FastAPI(title="Calculadora Ganadera")

app.include_router(health.router)
app.include_router(auth.router)
