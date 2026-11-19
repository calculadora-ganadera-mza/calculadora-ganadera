from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AnimalCategory, Parameter
from app.schemas.animal_category import AnimalCategoryUpdate


class ReferenceNotFoundError(LookupError):
    """El parámetro o la categoría no existe."""


class InvalidParameterValueError(ValueError):
    """El valor no cumple la regla de la tabla parameter."""


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
    parameter.value = value
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as err:
        raise InvalidParameterValueError(
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
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            raise InvalidParameterValueError(f"El campo {field} no puede quedar vacío.")
        setattr(category, field, value)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as err:
        raise DuplicateCategoryNameError(
            "Ya existe una categoría con ese nombre."
        ) from err
    return category
