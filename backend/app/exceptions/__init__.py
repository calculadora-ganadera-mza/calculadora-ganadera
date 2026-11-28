from app.exceptions.auth import (
    EmailAlreadyRegisteredError,
    EmailAlreadyVerifiedError,
    ExpiredOrRevokedRefreshTokenError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidPasswordResetCodeError,
    InvalidRefreshTokenError,
    InvalidVerificationCodeError,
    TokenUserNotFoundError,
    TooManyCodesError,
)
from app.exceptions.base import (
    AppError,
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
    RateLimitError,
)
from app.exceptions.carrying_capacity import (
    CalculationNotFoundError,
    NotCalculableError,
    SeasonNotFoundError,
    UnsupportedSeasonUpdateError,
)
from app.exceptions.herds import (
    HerdExistsError,
    InvalidHerdError,
    UnitNotFoundError,
)
from app.exceptions.production_units import InvalidPolygonError
from app.exceptions.reference_data import (
    DuplicateCategoryNameError,
    InvalidReferenceValueError,
    ReferenceNotFoundError,
)
from app.exceptions.scenarios import (
    InvalidFirstSeasonYearError,
    SeasonExistsError,
)
from app.exceptions.water_points import (
    InvalidWaterPointError,
    WaterPointNotFoundError,
)

__all__ = [
    "AppError",
    "AuthenticationError",
    "CalculationNotFoundError",
    "ConflictError",
    "DomainValidationError",
    "DuplicateCategoryNameError",
    "EmailAlreadyRegisteredError",
    "EmailAlreadyVerifiedError",
    "ExpiredOrRevokedRefreshTokenError",
    "HerdExistsError",
    "InvalidAccessTokenError",
    "InvalidCredentialsError",
    "InvalidFirstSeasonYearError",
    "InvalidHerdError",
    "InvalidPasswordResetCodeError",
    "InvalidPolygonError",
    "InvalidReferenceValueError",
    "InvalidRefreshTokenError",
    "InvalidVerificationCodeError",
    "InvalidWaterPointError",
    "NotCalculableError",
    "NotFoundError",
    "RateLimitError",
    "ReferenceNotFoundError",
    "SeasonExistsError",
    "SeasonNotFoundError",
    "TokenUserNotFoundError",
    "TooManyCodesError",
    "UnitNotFoundError",
    "UnsupportedSeasonUpdateError",
    "WaterPointNotFoundError",
]
