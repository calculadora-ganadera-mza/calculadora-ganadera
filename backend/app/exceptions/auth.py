from app.exceptions.base import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    RateLimitError,
)


class InvalidCredentialsError(AuthenticationError):
    """Las credenciales de inicio de sesión no son válidas."""


class EmailAlreadyRegisteredError(ConflictError):
    """Ya existe una cuenta registrada con ese correo."""


class InvalidRefreshTokenError(AuthenticationError):
    """El token de renovación no existe o no es válido."""


class ExpiredOrRevokedRefreshTokenError(AuthenticationError):
    """La sesión de renovación venció o fue revocada."""


class EmailAlreadyVerifiedError(ConflictError):
    """El correo del usuario ya está verificado."""


class InvalidVerificationCodeError(DomainValidationError):
    """El código no coincide, venció o se le agotaron los intentos."""


class TooManyCodesError(RateLimitError):
    """Se pidió un código antes de la espera o por encima del máximo por hora."""


class InvalidPasswordResetCodeError(DomainValidationError):
    """El código no coincide, venció, ya fue usado o se le agotaron los intentos."""


class InvalidAccessTokenError(AuthenticationError):
    """El token de acceso no es válido o no incluye al usuario."""


class TokenUserNotFoundError(AuthenticationError):
    """El usuario indicado en el token de acceso no existe."""
