"""Workflow management service."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.workflow import Workflow, WorkflowStep

logger = structlog.get_logger(__name__)


async def list_workflows(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Workflow]:
    """Return all workflows for *org_id*."""
    stmt = select(Workflow).where(Workflow.org_id == org_id).order_by(Workflow.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
) -> Workflow:
    """Return a single workflow with its steps.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if wf is None:
        raise NotFoundError(f"Workflow {workflow_id} not found.")
    return wf


async def create_workflow(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> Workflow:
    """Create a new workflow with optional steps."""
    wf = Workflow(
        org_id=org_id,
        name=data["name"],
        description=data.get("description"),
        trigger_type=data["trigger_type"],
        trigger_config=data.get("trigger_config", {}),
        is_active=data.get("is_active", False),  # new workflows start inactive
        version=1,
    )
    db.add(wf)
    await db.flush()

    # Create steps if provided
    steps_data = data.get("steps", [])
    for idx, step_data in enumerate(steps_data):
        step = WorkflowStep(
            workflow_id=wf.id,
            step_order=step_data.get("step_order", idx),
            step_type=step_data["step_type"],
            config=step_data.get("config", {}),
            timeout_seconds=step_data.get("timeout_seconds"),
        )
        db.add(step)

    if steps_data:
        await db.flush()

    logger.info("workflow_created", workflow_id=str(wf.id), name=wf.name)
    return wf


async def update_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    data: dict,
) -> Workflow:
    """Partially update a workflow's configuration.

    If ``steps`` is provided the existing steps are replaced wholesale.
    """
    wf = await get_workflow(db, workflow_id)

    for field in ("name", "description", "trigger_type", "trigger_config"):
        if field in data and data[field] is not None:
            setattr(wf, field, data[field])

    # Replace steps if provided
    if "steps" in data:
        # Remove existing steps
        for old_step in list(wf.steps):
            await db.delete(old_step)
        await db.flush()

        for idx, step_data in enumerate(data["steps"]):
            step = WorkflowStep(
                workflow_id=wf.id,
                step_order=step_data.get("step_order", idx),
                step_type=step_data["step_type"],
                config=step_data.get("config", {}),
                on_success_step_id=step_data.get("on_success_step_id"),
                on_failure_step_id=step_data.get("on_failure_step_id"),
                timeout_seconds=step_data.get("timeout_seconds"),
            )
            db.add(step)

        wf.version += 1

    db.add(wf)
    await db.flush()

    logger.info("workflow_updated", workflow_id=str(wf.id))
    return wf


async def delete_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
) -> None:
    """Delete a workflow and all its steps."""
    wf = await get_workflow(db, workflow_id)

    # Cascade should handle steps, but be explicit
    for step in list(wf.steps):
        await db.delete(step)

    await db.delete(wf)
    await db.flush()

    logger.info("workflow_deleted", workflow_id=str(workflow_id))


async def activate_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    is_active: bool,
) -> Workflow:
    """Activate or deactivate a workflow.

    Validates that the workflow has at least one step before activation.
    """
    wf = await get_workflow(db, workflow_id)

    if is_active and not wf.steps:
        raise ValidationError(
            "Cannot activate a workflow with no steps. Add at least one step first."
        )

    wf.is_active = is_active
    db.add(wf)
    await db.flush()

    state = "activated" if is_active else "deactivated"
    logger.info(f"workflow_{state}", workflow_id=str(wf.id))
    return wf
