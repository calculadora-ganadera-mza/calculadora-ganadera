from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
    RateLimitError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra la traducción de excepciones del dominio a respuestas HTTP."""

    @app.exception_handler(AuthenticationError)
    async def unauthorized_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(DomainValidationError)
    async def unprocessable_handler(
        request: Request, exc: DomainValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RateLimitError)
    async def too_many_requests_handler(
        request: Request, exc: RateLimitError
    ) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."},
        )
