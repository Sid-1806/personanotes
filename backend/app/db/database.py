from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

# Ensure we use asyncpg driver for async sessions
DATABASE_URL = (
    os.getenv("DATABASE_URL", "")
    .replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    .replace("postgresql://", "postgresql+asyncpg://")
)

engine = create_async_engine(DATABASE_URL)

SessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    # Keep ORM attributes usable after commit. With the async engine, a lazy
    # reload of an expired attribute (the default expire_on_commit=True) happens
    # via synchronous attribute access and raises MissingGreenlet. Disabling
    # expiry lets code safely read e.g. current_user.id / lecture.id post-commit.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# A synchronous engine/session for background workers that run in a threadpool
# (they can't use the async session). Uses the psycopg2 driver.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SYNC_DATABASE_URL = (
    os.getenv("DATABASE_URL", "")
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    .replace("postgresql://", "postgresql+psycopg2://")
)
sync_engine = create_engine(SYNC_DATABASE_URL)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)
