"""AutonoCX ORM models.

Importing this package ensures every model is registered with the shared
``Base.metadata`` so that Alembic's ``--autogenerate`` can discover them.
"""

from .base import Base, TimestampMixin

# Domain models ---------------------------------------------------------
from .organization import Organization, PlanType
from .user import User, UserRole
from .agent import AgentConfig
from .conversation import (
    ChannelType,
    ContentType,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    Priority,
)
from .tool import RiskLevel, Tool
from .action import ActionExecution, ActionStatus
from .knowledge import Document, DocumentChunk, DocumentStatus, KnowledgeBase
from .workflow import StepType, TriggerType, Workflow, WorkflowStep
from .channel import ChannelConfig
from .prompt import PromptCategory, PromptTemplate, PromptVersion
from .audit import ActorType, AuditLog
from .analytics import (
    CustomerMemory,
    MemoryType,
    MetricPeriod,
    MetricSnapshot,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Organization
    "Organization",
    "PlanType",
    # User
    "User",
    "UserRole",
    # Agent
    "AgentConfig",
    # Conversation
    "Conversation",
    "Message",
    "ChannelType",
    "ConversationStatus",
    "Priority",
    "MessageRole",
    "ContentType",
    # Tool
    "Tool",
    "RiskLevel",
    # Action
    "ActionExecution",
    "ActionStatus",
    # Knowledge
    "KnowledgeBase",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    # Workflow
    "Workflow",
    "WorkflowStep",
    "TriggerType",
    "StepType",
    # Channel
    "ChannelConfig",
    # Prompt
    "PromptTemplate",
    "PromptVersion",
    "PromptCategory",
    # Audit
    "AuditLog",
    "ActorType",
    # Analytics
    "MetricSnapshot",
    "MetricPeriod",
    "CustomerMemory",
    "MemoryType",
]
