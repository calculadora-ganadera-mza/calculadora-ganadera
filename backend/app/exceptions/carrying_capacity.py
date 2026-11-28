from app.exceptions.base import DomainValidationError, NotFoundError


class NotCalculableError(DomainValidationError):
    """Faltan datos para calcular la receptividad."""


class CalculationNotFoundError(NotFoundError):
    """El cálculo guardado no existe o no pertenece al usuario."""


class SeasonNotFoundError(NotFoundError):
    """La campaña no existe o no pertenece al establecimiento del sector."""


class UnsupportedSeasonUpdateError(DomainValidationError):
    """La actualización de campaña al guardar todavía no está implementada."""
