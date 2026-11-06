from app.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserPublic
from app.core.db import SessionDep

class UserService:
    def __init__(self, session: SessionDep):
        self.user_repository = UserRepository(session)
    
    def create_user(self, user: User) -> UserPublic:
        return self.user_repository.create_user(user)

    def get_user_by_email(self, email: str) -> UserPublic:
        return self.user_repository.get_user_by_email(email)

    def get_user_by_id(self, user_id: int) -> UserPublic:
        return self.user_repository.get_user_by_id(user_id)