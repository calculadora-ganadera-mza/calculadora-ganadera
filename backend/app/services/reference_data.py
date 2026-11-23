from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import violated_constraint
from app.models import AnimalCategory, Parameter
from app.schemas.animal_category import AnimalCategoryUpdate
from app.services.carrying_capacity import check_calculation_parameters


class ReferenceNotFoundError(LookupError):
    """El parámetro o la categoría no existe."""


class InvalidReferenceValueError(ValueError):
    """El valor no cumple una regla de los valores de referencia."""


class DuplicateCategoryNameError(ValueError):
    """Ya existe otra categoría con ese nombre."""


def list_parameters(session: Session) -> list[Parameter]:
    """Parámetros de cálculo, ordenados por clave."""
    return list(session.scalars(select(Parameter).order_by(Parameter.key)))


def list_animal_categories(session: Session) -> list[AnimalCategory]:
    return list(session.scalars(select(AnimalCategory).order_by(AnimalCategory.id)))


def update_parameter(session: Session, key: str, value: float | None) -> Parameter:
    """Cambia el valor; el próximo cálculo lo lee de la tabla.

    La regla de qué parámetros pueden quedar sin valor vive en la restricción
    ck_parameter_value_positive de la base, para no repetirla acá.
    """
    parameter = session.scalar(select(Parameter).where(Parameter.key == key))
    if parameter is None:
        raise ReferenceNotFoundError("Parámetro no encontrado.")
    try:
        # El cambio va dentro del savepoint: si algo falla, el valor vuelve atrás
        with session.begin_nested():
            parameter.value = value
            session.flush()
            try:
                check_calculation_parameters(session)
            except ValidationError as err:
                raise InvalidReferenceValueError(
                    "El valor no es válido para este parámetro: los meses van de "
                    "1 a 12, los días y las edades son números enteros y el umbral "
                    "de carga es una fracción mayor que 0 y menor o igual a 1."
                ) from err
    except IntegrityError as err:
        if violated_constraint(err) != "ck_parameter_value_positive":
            raise
        # El esquema ya exige mayor que 0: lo único que llega acá es un None
        raise InvalidReferenceValueError(
            "Solo los índices pueden quedar sin valor."
        ) from err
    return parameter


def update_animal_category(
    session: Session, category_id: int, data: AnimalCategoryUpdate
) -> AnimalCategory:
    """Cambia los campos enviados de la categoría."""
    category = session.get(AnimalCategory, category_id)
    if category is None:
        raise ReferenceNotFoundError("Categoría no encontrada.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None:
            raise InvalidReferenceValueError(f"El campo {field} no puede quedar vacío.")
    try:
        # El cambio va dentro del savepoint: si la base lo rechaza, vuelve atrás
        with session.begin_nested():
            for field, value in changes.items():
                setattr(category, field, value)
            session.flush()
    except IntegrityError as err:
        if violated_constraint(err) != "uq_animal_category_name":
            raise
        raise DuplicateCategoryNameError(
            "Ya existe una categoría con ese nombre."
        ) from err
    return category
