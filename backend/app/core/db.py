from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def violated_constraint(err: IntegrityError) -> str | None:
    """Nombre de la restricción de la base que rechazó el cambio."""
    diag = getattr(err.orig, "diag", None)
    return getattr(diag, "constraint_name", None)
