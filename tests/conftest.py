import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure the backend root (qual-backend) is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set test environment defaults before any app modules configure settings
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-qual-dev-change-in-production")
os.environ.setdefault("COOKIE_SECURE", "false")

from app.app import app
from app.database.sql.db import Base, get_db
from app.database.sql.models.course import Chapter, Module, Topic, UserTopicProgress  # noqa: F401
from app.database.sql.models.refresh_token import RefreshToken  # noqa: F401
from app.database.sql.models.user import User as UserModel
from app.services.auth import create_access_token, hash_password
from app.services.csrf import generate_csrf_token


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Session-scoped in-memory SQLite async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Function-scoped AsyncSession connected to test engine.
    Rolls back any changes made during the test.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = session_maker()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserModel:
    """Creates and persists a standard test user."""
    user = UserModel(
        username="quantum_tester",
        email="test@qual.dev",
        password=hash_password("SecurePassword123!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: UserModel) -> str:
    """Generates a valid JWT access token for test_user."""
    return create_access_token(user_id=test_user.id, email=test_user.email)


@pytest.fixture
def auth_headers(test_user_token: str) -> dict[str, str]:
    """Authorization header with Bearer token."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def csrf_token_value() -> str:
    """Generates a valid cryptographic CSRF token."""
    return generate_csrf_token()


@pytest.fixture
def csrf_headers(csrf_token_value: str) -> dict[str, str]:
    """X-CSRF-Token header."""
    return {"X-CSRF-Token": csrf_token_value}


@pytest.fixture
def client(db_session: AsyncSession):
    """
    FastAPI TestClient with get_db dependency overridden to use the test session.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

