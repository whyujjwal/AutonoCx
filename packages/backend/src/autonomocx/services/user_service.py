"""User management service."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import ConflictError, NotFoundError
from autonomocx.core.security import get_password_hash
from autonomocx.models.user import User, UserRole
from autonomocx.schemas.common import PaginatedResponse

logger = structlog.get_logger(__name__)


async def get_users(
    db: AsyncSession,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """Return a paginated list of users belonging to *org_id*."""
    base = select(User).where(User.org_id == org_id)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated rows
    stmt = (
        base
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    return PaginatedResponse.create(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User:
    """Fetch a single user by primary key.

    Raises ``NotFoundError`` if the user does not exist.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError(f"User {user_id} not found.")
    return user


async def create_user(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_data,  # UserCreate schema or dict-like
) -> User:
    """Create a new user inside an organization.

    A temporary random password is generated; the user should reset it
    on first login.  Raises ``ConflictError`` if the email is taken.
    """
    # Normalise input -- accept both Pydantic models and plain dicts
    data = user_data if isinstance(user_data, dict) else user_data.model_dump()

    # Duplicate email check
    existing = await db.execute(
        select(User).where(User.email == data["email"])
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"Email {data['email']} is already registered.")

    # Generate a temporary password hash (user should reset via email flow)
    temp_password = uuid.uuid4().hex[:16]

    user = User(
        org_id=org_id,
        email=data["email"],
        password_hash=get_password_hash(temp_password),
        full_name=data["full_name"],
        role=data.get("role", UserRole.VIEWER),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    logger.info("user_created", user_id=str(user.id), email=user.email, org_id=str(org_id))
    return user


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_data,  # UserUpdate schema or dict-like
) -> User:
    """Partially update a user's mutable fields."""
    user = await get_user_by_id(db, user_id)
    data = user_data if isinstance(user_data, dict) else user_data.model_dump(exclude_unset=True)

    for field in ("full_name", "role", "is_active"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])

    db.add(user)
    await db.flush()

    logger.info("user_updated", user_id=str(user.id))
    return user


async def change_user_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRole,
) -> User:
    """Change a user's role.

    Raises ``NotFoundError`` if the user does not exist.
    """
    user = await get_user_by_id(db, user_id)
    user.role = role
    db.add(user)
    await db.flush()

    logger.info("user_role_changed", user_id=str(user.id), new_role=role.value)
    return user
