from app.exceptions.base import ConflictError, DomainValidationError, NotFoundError


class InvalidHerdError(DomainValidationError):
    """Los datos del rodeo no cumplen una regla del contrato."""


class HerdExistsError(ConflictError):
    """El sector ya tiene un rodeo en esa campaña."""


class UnitNotFoundError(NotFoundError):
    """El sector no existe o no es del establecimiento de la campaña."""
