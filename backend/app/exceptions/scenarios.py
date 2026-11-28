from app.exceptions.base import ConflictError, DomainValidationError


class InvalidFirstSeasonYearError(DomainValidationError):
    """El año elegido para la primera campaña no está entre los permitidos."""


class SeasonExistsError(ConflictError):
    """El establecimiento ya tiene una campaña para ese año."""
