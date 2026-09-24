from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class ChatThread(Base):
    """A question-and-answer conversation scoped to part of the user's corpus.

    ``scope`` is one of ``note`` | ``lecture`` | ``course`` | ``all`` and decides
    which retrieval filter the answer is grounded in. The matching id column is
    populated for the narrower scopes.
    """

    __tablename__ = "chat_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scope = Column(String, nullable=False, server_default="all")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=True, index=True)
    note_id = Column(Integer, ForeignKey("generated_notes.id"), nullable=True, index=True)
    title = Column(String, nullable=False, server_default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    """One turn in a thread. Assistant turns carry their retrieval citations."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(
        Integer, ForeignKey("chat_threads.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(String, nullable=False)
    # [{lecture_id, lecture_title, text, score}] for assistant turns
    citations = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
