from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health
from app.core.db import create_db_and_tables
from app.core.exception_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Calculadora Ganadera", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
