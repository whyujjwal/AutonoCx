"""Abstract LLM provider interface and shared data models."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A single tool/function call requested by the LLM."""

    id: str
    name: str
    arguments: dict


@dataclass(slots=True)
class LLMRequest:
    """Normalised request payload accepted by every LLM provider."""

    messages: list[dict]  # [{"role": "system", "content": "..."}, ...]
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048
    tools: list[dict] | None = None  # OpenAI-format tool definitions
    stream: bool = False
    # Optional metadata carried through for logging / billing
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class LLMResponse:
    """Normalised response returned by every LLM provider."""

    content: str = ""
    tool_calls: list[ToolCall] | None = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    request_id: str = ""
    finish_reason: str = ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class BaseLLMProvider(ABC):
    """Contract that every LLM provider must implement."""

    name: str = "base"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a chat-completion request and return the full response."""
        ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Yield content deltas as they arrive from the provider."""
        ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Return estimated cost in USD for the given token counts."""
        ...

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports function/tool calling."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_ms() -> int:
        """Return current time in milliseconds (monotonic)."""
        return int(time.monotonic() * 1000)
