from datetime import datetime, timezone, timedelta
from typing import Annotated
import jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from app.schemas.auth import  TokenData
from app.services.user import UserService
from app.core.db import SessionDep
from app.models.user import User
from app.schemas.user import UserPublic
from app.core.config import settings
from app.exceptions import CredentialsError, UnauthorizedError


ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> User:
    user_service = UserService(session)
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise CredentialsError('Payload is missing user id')
        token_data = TokenData(id=user_id)
    except jwt.InvalidTokenError:
        raise CredentialsError('Invalid token')
    user = user_service.get_user_by_id(token_data.id)
    return user 

def get_current_active_user(current_user: Annotated[UserPublic, Depends(get_current_user)]):
    return current_user


