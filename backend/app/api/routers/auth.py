from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.token import Token

router = APIRouter()


class RegisterResponse(BaseModel):
    """A new account plus its session token."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterResponse)
async def register_user(
    user_in: UserCreate, db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Register a new user in the system.

    Args:
        user_in (UserCreate): The registration data payload (name, email, password).
        db (AsyncSession): The database session.

    Returns:
        Any: The new user plus an access token, so the client can go straight
        into onboarding instead of bouncing the user to a login form.

    Raises:
        HTTPException: If the email is already registered.
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    # Create new user
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Sign the user in immediately. Making someone re-enter credentials they
    # typed five seconds ago adds a step and no security.
    return RegisterResponse(
        user=UserResponse.model_validate(new_user),
        access_token=create_access_token(subject=new_user.id),
        token_type="bearer",
    )


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    Authenticate user and return a JWT access token.

    Args:
        db (AsyncSession): The database session.
        form_data (OAuth2PasswordRequestForm): Standard OAuth2 form data containing username (email) and password.

    Returns:
        Any: A dictionary containing the access token and token type.
        
    Raises:
        HTTPException: If authentication fails.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use the immutable user id as the token subject (not the mutable email).
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
