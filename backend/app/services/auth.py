import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.password import hash_password, verify_password
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.user import UserCreate


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def issue(
        self,
        user: User,
        family_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[str, str]:
        access = create_access_token({"sub": str(user.id)})
        refresh = secrets.token_urlsafe(48)
        self.session.add(
            RefreshSession(
                user_id=user.id,
                token_hash=token_hash(refresh),
                family_id=family_id or str(uuid4()),
                expires_at=expires_at
                or datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
                revoked=False,
            )
        )
        return access, refresh

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.session.scalar(select(User).where(User.email == email.lower()))
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(401, "Credenciales inválidas")
        tokens = self.issue(user)
        self.session.commit()
        return tokens

    def register(self, data: UserCreate) -> tuple[str, str]:
        user = User(
            name=data.name,
            email=str(data.email).lower(),
            password_hash=hash_password(data.password),
        )
        self.session.add(user)
        try:
            self.session.flush()
            tokens = self.issue(user)
            self.session.commit()
            return tokens
        except IntegrityError:
            self.session.rollback()
            raise HTTPException(409, "El correo ya está registrado") from None

    def find_locked(self, token: str) -> RefreshSession | None:
        record = self.session.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash(token))
        )
        if record:
            # Bloquea primero el usuario para serializar la rotación
            # y la revocación de la familia.
            self.session.scalar(
                select(User).where(User.id == record.user_id).with_for_update()
            )
            self.session.refresh(record)
        return record

    def revoke_family(self, family_id: str) -> None:
        self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id)
            .values(revoked=True)
        )

    def refresh(self, token: str) -> tuple[str, str]:
        record = self.find_locked(token)
        if record is None:
            raise HTTPException(401, "Token de renovación inválido")
        user = self.session.get(User, record.user_id)
        expiry = record.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if record.revoked or expiry <= datetime.now(UTC) or not user:
            self.revoke_family(record.family_id)
            self.session.commit()
            raise HTTPException(401, "La sesión de renovación venció o fue revocada")
        record.revoked = True
        tokens = self.issue(user, record.family_id, record.expires_at)
        self.session.commit()
        return tokens

    def logout(self, token: str) -> None:
        record = self.find_locked(token)
        if record:
            self.revoke_family(record.family_id)
            self.session.commit()
