from fastapi.exceptions import HTTPException
from app.exceptions import LoginError, RegisterError, NotFoundError, UnauthorizedError, ForbiddenError, CredentialsError, AppError
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

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
        