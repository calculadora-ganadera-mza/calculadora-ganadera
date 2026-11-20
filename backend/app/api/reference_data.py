from fastapi import APIRouter, HTTPException

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.schemas.animal_category import AnimalCategoryRead, AnimalCategoryUpdate
from app.schemas.parameter import ParameterRead, ParameterUpdate
from app.services.reference_data import (
    DuplicateCategoryNameError,
    InvalidReferenceValueError,
    ReferenceNotFoundError,
    list_animal_categories,
    list_parameters,
    update_animal_category,
    update_parameter,
)

# Valores de referencia: los lee cualquier usuario con sesión y los edita el
# administrador.
router = APIRouter(tags=["reference-data"])


@router.get("/parameters")
def read_parameters(session: SessionDep, user: CurrentUser) -> list[ParameterRead]:
    """Parámetros de cálculo, ordenados por clave."""
    return [ParameterRead.model_validate(p) for p in list_parameters(session)]


@router.patch("/parameters/{key}")
def edit_parameter(
    key: str, data: ParameterUpdate, session: SessionDep, admin: AdminUser
) -> ParameterRead:
    """Cambia el valor de un parámetro. El próximo cálculo usa el valor nuevo."""
    try:
        parameter = update_parameter(session, key, data.value)
    except ReferenceNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    except InvalidReferenceValueError as err:
        raise HTTPException(422, str(err)) from err
    session.commit()
    return ParameterRead.model_validate(parameter)


@router.get("/animal-categories")
def read_animal_categories(
    session: SessionDep, user: CurrentUser
) -> list[AnimalCategoryRead]:
    """Categorías de animales, para el formulario del rodeo y la administración."""
    return [
        AnimalCategoryRead.model_validate(category)
        for category in list_animal_categories(session)
    ]


@router.patch("/animal-categories/{animal_category_id}")
def edit_animal_category(
    animal_category_id: int,
    data: AnimalCategoryUpdate,
    session: SessionDep,
    admin: AdminUser,
) -> AnimalCategoryRead:
    """Cambia el nombre, el EV o el agua de una categoría. El código no cambia."""
    try:
        category = update_animal_category(session, animal_category_id, data)
    except ReferenceNotFoundError as err:
        raise HTTPException(404, str(err)) from err
    except InvalidReferenceValueError as err:
        raise HTTPException(422, str(err)) from err
    except DuplicateCategoryNameError as err:
        raise HTTPException(409, str(err)) from err
    session.commit()
    return AnimalCategoryRead.model_validate(category)
