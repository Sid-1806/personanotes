from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    """
    SQLAlchemy model representing a user in the system.

    Attributes:
        id (int): Primary key.
        name (str): Full name of the user.
        email (str): Unique email address used for login.
        hashed_password (str): Bcrypt hashed password.
        created_at (datetime): Timestamp when the user was created.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
