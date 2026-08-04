from typing import Any
from fastapi import APIRouter, Depends
from app.api import deps
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(deps.get_current_user)) -> Any:
    """
    Retrieve the profile of the currently authenticated user.

    Args:
        current_user (User): The authenticated user instance injected by dependencies.

    Returns:
        Any: The user data serialized by UserResponse.
    """
    return current_user
