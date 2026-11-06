from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.db import SessionDep
from app.core.jwt import get_current_user
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"


def check_origin(request: Request) -> None:
    # Browser clients must send an explicitly trusted Origin, including via proxy.
    if request.headers.get("origin") not in settings.AUTH_ALLOWED_ORIGINS:
        raise HTTPException(403, "Untrusted request origin")


def token_response(response: Response, tokens: tuple[str, str]) -> Token:
    access, refresh = tokens
    response.set_cookie(
        COOKIE,
        refresh,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return Token(access_token=access, token_type="bearer")


@router.post("/login", response_model=Token, dependencies=[Depends(check_origin)])
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    response: Response,
) -> Token:
    return token_response(
        response, AuthService(session).login(form_data.username, form_data.password)
    )


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    dependencies=[Depends(check_origin)],
)
def register(user: UserCreate, session: SessionDep, response: Response) -> Token:
    return token_response(response, AuthService(session).register(user))


@router.post("/refresh", response_model=Token, dependencies=[Depends(check_origin)])
def refresh(request: Request, response: Response, session: SessionDep) -> Token:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Missing refresh token")
    return token_response(response, AuthService(session).refresh(token))


@router.post("/logout", status_code=204, dependencies=[Depends(check_origin)])
def logout(request: Request, response: Response, session: SessionDep) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        AuthService(session).logout(token)
    response.delete_cookie(
        COOKIE,
        path="/",
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


@router.get("/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email}
