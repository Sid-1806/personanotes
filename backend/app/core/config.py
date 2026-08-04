from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and configuration mapped from environment variables.

    Attributes:
        PROJECT_NAME (str): Name of the project.
        API_V1_STR (str): Base path for API v1 routes.
        SECRET_KEY (str): Secret key for JWT encoding.
        ALGORITHM (str): JWT signing algorithm.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Token expiration duration in minutes.
        POSTGRES_USER (str): PostgreSQL username.
        POSTGRES_PASSWORD (str): PostgreSQL password.
        POSTGRES_SERVER (str): PostgreSQL server address.
        POSTGRES_PORT (int): PostgreSQL port.
        POSTGRES_DB (str): PostgreSQL database name.
        DATABASE_URL (str): Full SQLAlchemy connection URL.
        QDRANT_URL (str | None): Qdrant vector database URL.
        EMBEDDING_MODEL_NAME (str): Name of the embedding model to use.
        QDRANT_COLLECTION_NAME (str): Name of the vector collection.
        GEMINI_API_KEY (str): API key for Gemini LLM integration.
    """
    PROJECT_NAME: str = "Personalized AI Notes Generator"
    API_V1_STR: str = "/api/v1"

    # Allowed browser origins for CORS. Explicit origins are required because the
    # app sends credentials; "*" + credentials is rejected by browsers.
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    DATABASE_URL: str

    QDRANT_URL: str | None = "http://localhost:6333"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    QDRANT_COLLECTION_NAME: str = "lecture_notes"

    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
