from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role

UserEmail = Annotated[EmailStr, Field(min_length=5, max_length=100)]
UserPassword = Annotated[str, Field(min_length=8, max_length=100)]


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: UserEmail


class UserCreate(UserBase):
    password: UserPassword


class UserRead(BaseModel):
    """Usuario con la sesión iniciada; corresponde a CurrentUser del contrato."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    email_verified: bool
