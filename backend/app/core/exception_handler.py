from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    AppError,
    CredentialsError,
    ForbiddenError,
    LoginError,
    NotFoundError,
    RegisterError,
)

ERROR_STATUS = {
    LoginError: 401,
    RegisterError: 400,
    NotFoundError: 404,
    CredentialsError: 401,
    ForbiddenError: 403,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def exception_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=ERROR_STATUS.get(type(exc), 500),
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )
