"""Prompt template and version management service."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import ConflictError, NotFoundError, ValidationError

# The prompt models are expected at autonomocx.models.prompt.
# If they do not exist yet the imports will fail at runtime but this
# service is written to match the ORM shapes referenced by the User
# and Organization models.
from autonomocx.models.prompt import PromptTemplate, PromptVersion

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# PromptTemplate CRUD
# ---------------------------------------------------------------------------

async def list_prompts(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[PromptTemplate]:
    """Return all prompt templates belonging to *org_id*."""
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.org_id == org_id)
        .order_by(PromptTemplate.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_prompt(
    db: AsyncSession,
    prompt_id: uuid.UUID,
) -> PromptTemplate:
    """Return a single prompt template.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise NotFoundError(f"Prompt template {prompt_id} not found.")
    return prompt


async def create_prompt(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> PromptTemplate:
    """Create a new prompt template with an initial draft version."""
    prompt = PromptTemplate(
        org_id=org_id,
        name=data["name"],
        description=data.get("description"),
        category=data.get("category"),
        is_active=data.get("is_active", True),
    )
    db.add(prompt)
    await db.flush()

    # Auto-create the first version if body content is provided
    if data.get("body"):
        v1 = PromptVersion(
            prompt_template_id=prompt.id,
            version_number=1,
            body=data["body"],
            variables=data.get("variables", []),
            is_published=False,
            change_notes="Initial version",
        )
        db.add(v1)
        await db.flush()

    logger.info("prompt_created", prompt_id=str(prompt.id), name=prompt.name)
    return prompt


async def update_prompt(
    db: AsyncSession,
    prompt_id: uuid.UUID,
    data: dict,
) -> PromptTemplate:
    """Partially update a prompt template's metadata (not versions)."""
    prompt = await get_prompt(db, prompt_id)

    for field in ("name", "description", "category", "is_active"):
        if field in data and data[field] is not None:
            setattr(prompt, field, data[field])

    db.add(prompt)
    await db.flush()

    logger.info("prompt_updated", prompt_id=str(prompt.id))
    return prompt


async def delete_prompt(
    db: AsyncSession,
    prompt_id: uuid.UUID,
) -> None:
    """Delete a prompt template and all its versions."""
    prompt = await get_prompt(db, prompt_id)

    # Delete versions first
    versions_stmt = select(PromptVersion).where(
        PromptVersion.prompt_template_id == prompt_id
    )
    versions = (await db.execute(versions_stmt)).scalars().all()
    for v in versions:
        await db.delete(v)

    await db.delete(prompt)
    await db.flush()

    logger.info("prompt_deleted", prompt_id=str(prompt_id))


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

async def _get_version(
    db: AsyncSession,
    version_id: uuid.UUID,
) -> PromptVersion:
    result = await db.execute(
        select(PromptVersion).where(PromptVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise NotFoundError(f"Prompt version {version_id} not found.")
    return version


async def create_version(
    db: AsyncSession,
    prompt_id: uuid.UUID,
    data: dict,
) -> PromptVersion:
    """Create a new draft version for a prompt template.

    The version number is auto-incremented from the latest version.
    """
    prompt = await get_prompt(db, prompt_id)

    # Determine next version number
    latest_stmt = (
        select(PromptVersion)
        .where(PromptVersion.prompt_template_id == prompt_id)
        .order_by(PromptVersion.version_number.desc())
        .limit(1)
    )
    latest = (await db.execute(latest_stmt)).scalar_one_or_none()
    next_version = (latest.version_number + 1) if latest else 1

    version = PromptVersion(
        prompt_template_id=prompt_id,
        version_number=next_version,
        body=data["body"],
        variables=data.get("variables", []),
        is_published=False,
        change_notes=data.get("change_notes", ""),
        created_by=data.get("created_by"),
    )
    db.add(version)
    await db.flush()

    logger.info(
        "prompt_version_created",
        prompt_id=str(prompt_id),
        version_number=next_version,
    )
    return version


async def publish_version(
    db: AsyncSession,
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PromptVersion:
    """Publish a prompt version, un-publishing any currently published version.

    Only one version can be published (active) per prompt template at a time.
    """
    # Verify prompt exists
    await get_prompt(db, prompt_id)

    version = await _get_version(db, version_id)
    if version.prompt_template_id != prompt_id:
        raise ValidationError("Version does not belong to the specified prompt template.")

    if version.is_published:
        raise ValidationError("This version is already published.")

    # Un-publish current published version(s)
    published_stmt = select(PromptVersion).where(
        PromptVersion.prompt_template_id == prompt_id,
        PromptVersion.is_published.is_(True),
    )
    published_versions = (await db.execute(published_stmt)).scalars().all()
    for pv in published_versions:
        pv.is_published = False
        db.add(pv)

    # Publish the target version
    version.is_published = True
    version.published_at = datetime.now(UTC)
    db.add(version)
    await db.flush()

    logger.info(
        "prompt_version_published",
        prompt_id=str(prompt_id),
        version_id=str(version_id),
        version_number=version.version_number,
    )
    return version


async def rollback_version(
    db: AsyncSession,
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PromptVersion:
    """Rollback to a previously published version.

    This is functionally identical to ``publish_version`` -- it
    un-publishes the current version and publishes the target version.
    """
    return await publish_version(db, prompt_id, version_id)
