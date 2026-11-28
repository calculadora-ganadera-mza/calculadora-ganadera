from app.exceptions.base import DomainValidationError, NotFoundError


class InvalidWaterPointError(DomainValidationError):
    """Ubicación de aguada fuera de la tolerancia del sector."""


class WaterPointNotFoundError(NotFoundError):
    """El recurso no existe o no pertenece al usuario."""
