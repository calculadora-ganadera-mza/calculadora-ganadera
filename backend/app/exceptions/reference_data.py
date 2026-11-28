from app.exceptions.base import ConflictError, DomainValidationError, NotFoundError


class ReferenceNotFoundError(NotFoundError):
    """El parámetro o la categoría no existe."""


class InvalidReferenceValueError(DomainValidationError):
    """El valor no cumple una regla de los valores de referencia."""


class DuplicateCategoryNameError(ConflictError):
    """Ya existe otra categoría con ese nombre."""
