from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.exception_handler import register_exception_handlers
from app.core.db import create_db_and_tables
from app.api import health
from app.api import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    
app = FastAPI(title="Calculadora Ganadera", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
