"""Shared pytest fixtures for the AutonoCX backend test suite.

Provides:
- ``test_engine``   -- An async SQLAlchemy engine connected to a test database
- ``db_session``    -- An async session with automatic rollback after each test
- ``client``        -- An ``httpx.AsyncClient`` wired to the FastAPI test app
- ``user_factory``  -- A factory helper to create ``User`` instances for tests
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Ensure test settings are applied before any application import
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-do-not-use-in-production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://autonomocx:autonomocx_dev@localhost:5432/autonomocx_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from autonomocx.core.security import get_password_hash  # noqa: E402
from autonomocx.models.base import Base  # noqa: E402
from autonomocx.models.organization import Organization, PlanType  # noqa: E402
from autonomocx.models.user import User, UserRole  # noqa: E402

# ---------------------------------------------------------------------------
# Engine & session fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create an async engine for the test database.

    Creates all tables at the start of the test session and drops them
    at the end.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Provide a transactional async session that rolls back after each test.

    Each test gets a clean database state without needing to truncate tables.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    await transaction.rollback()
    await connection.close()


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Provide an ``httpx.AsyncClient`` connected to the FastAPI app.

    The app's ``get_db`` dependency is overridden to use the test session,
    ensuring all HTTP tests operate within the same rolled-back transaction.
    """
    # Lazy import to avoid circular imports and ensure env vars are set
    from autonomocx.core.database import get_db

    # Import or create the FastAPI app
    try:
        from autonomocx.main import app
    except ImportError:
        from fastapi import FastAPI

        app = FastAPI()

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factory fixtures
# ---------------------------------------------------------------------------


class UserFactory:
    """Helper to create ``User`` (and ``Organization``) instances for tests."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._counter = 0

    async def create(
        self,
        *,
        email: str | None = None,
        password: str = "testpass123!",
        full_name: str = "Test User",
        role: UserRole = UserRole.ADMIN,
        is_active: bool = True,
        org: Organization | None = None,
    ) -> User:
        """Create and persist a ``User`` with an associated ``Organization``.

        If no *org* is provided, a new one is created automatically.
        """
        self._counter += 1

        if org is None:
            org = Organization(
                id=uuid.uuid4(),
                name=f"Test Org {self._counter}",
                slug=f"test-org-{self._counter}-{uuid.uuid4().hex[:6]}",
                plan=PlanType.STARTER,
                is_active=True,
                settings={},
            )
            self._db.add(org)
            await self._db.flush()

        if email is None:
            email = f"testuser-{self._counter}-{uuid.uuid4().hex[:6]}@test.com"

        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=role,
            is_active=is_active,
        )
        self._db.add(user)
        await self._db.flush()
        return user


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession) -> UserFactory:
    """Provide a ``UserFactory`` bound to the current test session."""
    return UserFactory(db_session)
