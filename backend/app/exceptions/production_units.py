from app.exceptions.base import DomainValidationError


class InvalidPolygonError(DomainValidationError):
    """El contorno no cumple las reglas para guardar un sector."""
