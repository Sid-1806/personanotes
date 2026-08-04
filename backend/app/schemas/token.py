from pydantic import BaseModel


class Token(BaseModel):
    """
    Schema for JWT access token.

    Attributes:
        access_token (str): The JWT string.
        token_type (str): Type of the token (e.g., 'bearer').
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Schema for payload data encoded within the JWT.

    Attributes:
        email (str | None): The subject email address, if present.
    """
    email: str | None = None
