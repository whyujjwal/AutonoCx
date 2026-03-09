"""AutonoCX ORM models.

Importing this package ensures every model is registered with the shared
``Base.metadata`` so that Alembic's ``--autogenerate`` can discover them.
"""

from .action import ActionExecution, ActionStatus
from .agent import AgentConfig
from .analytics import (
    CustomerMemory,
    MemoryType,
    MetricPeriod,
    MetricSnapshot,
)
from .audit import ActorType, AuditLog
from .base import Base, TimestampMixin
from .channel import ChannelConfig
from .connector import ConnectorConfig
from .conversation import (
    ChannelType,
    ContentType,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    Priority,
)
from .knowledge import Document, DocumentChunk, DocumentStatus, KnowledgeBase

# Domain models ---------------------------------------------------------
from .organization import Organization, PlanType
from .prompt import PromptCategory, PromptTemplate, PromptVersion
from .tool import RiskLevel, Tool
from .user import User, UserRole
from .workflow import StepType, TriggerType, Workflow, WorkflowStep

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
    # Connector
    "ConnectorConfig",
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
