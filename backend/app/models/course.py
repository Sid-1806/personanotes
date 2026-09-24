from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class Course(Base):
    """A subject that groups lectures and the notes generated from them.

    Courses are the organising unit students actually think in. Every user gets
    an "Uncategorized" course created by the migration backfill so a flat
    lecture list keeps working.

    Attributes:
        id (int): Primary key.
        user_id (int): Owner.
        name (str): Display name, e.g. "Machine Learning".
        code (str | None): Optional course code, e.g. "CS229".
        color (str): Accent token used by the UI (see frontend COURSE_COLORS).
        archived (bool): Hidden from the default course list when true.
    """

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    color = Column(String, nullable=False, server_default="indigo")
    archived = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
