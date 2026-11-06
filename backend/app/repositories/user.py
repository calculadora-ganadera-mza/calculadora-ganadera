from sqlalchemy import select

from app.core.db import SessionDep
from app.models.user import User


class UserRepository:
    def __init__(self, session: SessionDep):
        self.session = session   

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.execute(
            select(User).where(User.email == email)
        ).scalars().first()

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.session.execute(
            select(User).where(User.id == user_id)
        ).scalars().first()
        