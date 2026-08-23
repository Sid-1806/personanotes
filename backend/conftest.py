import os
import sys

# Ensure the backend root is on sys.path so `import app...` resolves when
# pytest collects tests from the tests/ directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Provide dummy settings so importing app.core.config works during tests without
# a real .env. Real environment variables (if set) still take precedence.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)
