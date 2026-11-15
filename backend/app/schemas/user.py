from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr = Field(min_length=5, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserRead(BaseModel):
    """Usuario con la sesión iniciada; corresponde a CurrentUser del contrato."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
