from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, EmailSenderDep, SessionDep
from app.core.config import settings
from app.schemas.auth import (
    EmailVerificationInput,
    ForgotPasswordInput,
    ResetPasswordInput,
    Token,
)
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService
from app.services.email_verification import (
    EmailAlreadyVerifiedError,
    EmailVerificationService,
    InvalidVerificationCodeError,
    TooManyCodesError,
    send_verification_code,
)
from app.services.password_reset import (
    InvalidPasswordResetCodeError,
    PasswordResetService,
    send_password_reset_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"


def check_origin(request: Request) -> None:
    # El navegador debe enviar un origen de confianza, incluso con un proxy.
    if request.headers.get("origin") not in settings.auth_allowed_origins:
        raise HTTPException(403, "Origen de la solicitud no permitido")


def token_response(response: Response, tokens: tuple[str, str]) -> Token:
    access, refresh = tokens
    response.set_cookie(
        COOKIE,
        refresh,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_days * 86400,
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
def register(
    user: UserCreate,
    session: SessionDep,
    response: Response,
    background_tasks: BackgroundTasks,
    sender: EmailSenderDep,
) -> Token:
    """Crea la cuenta e inicia la sesión. El código se manda después de responder."""
    new_user, tokens = AuthService(session).register(user)
    code = EmailVerificationService(session).create_code(new_user)
    session.commit()
    background_tasks.add_task(send_verification_code, sender, new_user.email, code)
    return token_response(response, tokens)


@router.post("/refresh", response_model=Token, dependencies=[Depends(check_origin)])
def refresh(request: Request, response: Response, session: SessionDep) -> Token:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Falta el token de renovación")
    return token_response(response, AuthService(session).refresh(token))


@router.post("/logout", status_code=204, dependencies=[Depends(check_origin)])
def logout(request: Request, response: Response, session: SessionDep) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        AuthService(session).logout(token)
    response.delete_cookie(
        COOKIE,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


@router.get("/me")
def me(user: CurrentUser) -> UserRead:
    """Datos del usuario con la sesión iniciada."""
    return UserRead.model_validate(user)


@router.post("/verify-email", status_code=204)
def verify_email(
    data: EmailVerificationInput, user: CurrentUser, session: SessionDep
) -> None:
    """Verifica el correo con el último código que se envió."""
    try:
        EmailVerificationService(session).verify(user, data.code)
    except EmailAlreadyVerifiedError as err:
        raise HTTPException(409, str(err)) from err
    except InvalidVerificationCodeError as err:
        # Guarda el intento fallido antes de responder.
        session.commit()
        raise HTTPException(422, str(err)) from err
    session.commit()


@router.post("/resend-verification", status_code=202, response_class=Response)
def resend_verification(
    user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    sender: EmailSenderDep,
) -> None:
    """Genera otro código y lo envía por correo después de responder."""
    try:
        code = EmailVerificationService(session).resend(user)
    except EmailAlreadyVerifiedError as err:
        raise HTTPException(409, str(err)) from err
    except TooManyCodesError as err:
        raise HTTPException(429, str(err)) from err
    session.commit()
    background_tasks.add_task(send_verification_code, sender, user.email, code)


@router.post(
    "/forgot-password",
    status_code=202,
    response_class=Response,
    dependencies=[Depends(check_origin)],
)
def forgot_password(
    data: ForgotPasswordInput,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    sender: EmailSenderDep,
) -> None:
    """Recibe el pedido y manda el código en segundo plano si corresponde."""
    result = PasswordResetService(session).request_code(str(data.email))
    if result is not None:
        to_email, code = result
        session.commit()
        background_tasks.add_task(send_password_reset_code, sender, to_email, code)


@router.post(
    "/reset-password",
    status_code=204,
    dependencies=[Depends(check_origin)],
)
def reset_password(data: ResetPasswordInput, session: SessionDep) -> None:
    """Cambia la contraseña con el último código vigente y cierra las sesiones."""
    try:
        PasswordResetService(session).reset_password(
            str(data.email), data.code, data.password
        )
    except InvalidPasswordResetCodeError as err:
        # Guarda el intento fallido antes de responder.
        session.commit()
        raise HTTPException(422, str(err)) from err
    session.commit()
