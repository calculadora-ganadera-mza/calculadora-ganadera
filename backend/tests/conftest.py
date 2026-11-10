import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def pytest_configure(config: pytest.Config) -> None:
    # Las pruebas usan una base aparte (<base>_test) para no tocar la de
    # desarrollo. Se cambia acá porque la app lee el nombre cuando se importa.
    settings.db_database += "_test"
    os.environ["DB_DATABASE"] = settings.db_database


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture(scope="session", autouse=True)
def database(alembic_config: Config) -> None:
    """Crea la base de pruebas si no existe y la lleva a la última migración."""
    url = settings.database_url
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def engine(database: None) -> Engine:
    from app.core.db import engine

    return engine


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Sesión dentro de una transaccion que se deshace al terminar la prueba."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def user(session: Session) -> User:
    user = User(name="Prueba", email="prueba@example.com", password_hash="x")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def other_user(session: Session) -> User:
    other = User(name="Otro", email="otro@example.com", password_hash="x")
    session.add(other)
    session.flush()
    return other


@pytest.fixture
def api(monkeypatch, session: Session, user: User):
    """Cliente de la API con la sesion de prueba y un usuario que inició sesión."""
    from app.core.db import get_session
    from app.core.jwt import create_access_token
    from app.main import app

    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-" * 5)
    app.dependency_overrides[get_session] = lambda: session
    token = create_access_token({"sub": str(user.id)})
    try:
        yield TestClient(app, headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
