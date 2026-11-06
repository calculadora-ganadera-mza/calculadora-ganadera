class AppError(Exception):
    code = "INTERNAL_SERVER_ERROR"
    message = "There has been an error"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class LoginError(AppError):
    code = "LOGIN_ERROR"
    message = "User not found or password is incorrect"


class RegisterError(AppError):
    code = "REGISTER_ERROR"
    message = "Register error"


class NotFoundError(AppError):
    code = "NOT_FOUND"
    message = "Not found"


class CredentialsError(AppError):
    code = "CREDENTIALS_ERROR"
    message = "Credentials error"


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED_ERROR"
    message = "Unauthorized"


class ForbiddenError(AppError):
    code = "FORBIDDEN_ERROR"
    message = "Forbidden"
