from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr = Field(min_length=5, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserPublic(UserBase):
    id: int
