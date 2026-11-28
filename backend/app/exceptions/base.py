class AppError(ValueError):
    """Error base de las reglas del dominio."""


class AuthenticationError(AppError):
    """Fallo de autenticación o sesión inválida."""


class NotFoundError(AppError):
    """El recurso pedido no existe o no pertenece al usuario."""


class ConflictError(AppError):
    """La operación choca con el estado actual o un dato único."""


class DomainValidationError(AppError):
    """Los datos o la operación no cumplen una regla del dominio."""


class RateLimitError(AppError):
    """Se superó el límite de intentos o pedidos en el período."""
