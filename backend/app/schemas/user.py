from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class UserBase(BaseModel):
    """
    Base Pydantic schema for User properties.

    Attributes:
        name (str): Full name of the user.
        email (EmailStr): Validated email address.
    """
    name: str
    email: EmailStr


class UserCreate(UserBase):
    """
    Schema for creating a new User.

    Attributes:
        password (str): Raw password string, will be hashed later.
    """
    password: str


class UserResponse(UserBase):
    """
    Schema for returning User data in API responses.

    Attributes:
        id (int): Primary key of the user.
        created_at (datetime): Timestamp when the user was created.
    """
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
