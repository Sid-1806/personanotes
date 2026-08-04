from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Lecture(Base):
    """
    SQLAlchemy model representing an uploaded lecture document.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key referencing the user who uploaded the lecture.
        filename (str): Original name of the uploaded file.
        filepath (str): Storage path of the file.
        filetype (str): MIME type or extension of the file.
        uploaded_at (datetime): Timestamp when the file was uploaded.
        user (User): Relationship to the uploading user.
    """
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="lectures")
