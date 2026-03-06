"""Context assembly -- builds the full message list fed to the LLM."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

import structlog

from autonomocx.models.analytics import CustomerMemory
from autonomocx.models.conversation import Message, MessageRole

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class RAGChunk:
    """Lightweight representation of a RAG retrieval result."""

    content: str
    source: str = ""
    score: float = 0.0


@dataclass(slots=True)
class AssembledContext:
    """The full context payload ready for the LLM."""

    messages: list[dict[str, Any]]
    token_estimate: int = 0
    rag_sources: list[str] = field(default_factory=list)


class ContextAssembler:
    """Builds the messages list that gets sent to the LLM.

    The final message structure:
    1. System prompt (agent personality + instructions)
    2. Long-term memory block (customer facts / preferences)
    3. RAG knowledge block (retrieved documents)
    4. Session state block (current conversation state)
    5. Conversation history (user/assistant turns)
    6. Current user message (already in history)
    """

    # Rough chars-per-token estimate for context budgeting
    _CHARS_PER_TOKEN = 4

    def assemble(
        self,
        *,
        system_prompt: str,
        conversation_history: Sequence[Message] | list[dict[str, Any]],
        session_memories: dict[str, Any] | None = None,
        long_term_memories: Sequence[CustomerMemory] | None = None,
        rag_results: list[RAGChunk] | None = None,
        agent_config: Any | None = None,
        max_history_turns: int = 20,
        max_context_tokens: int = 8000,
    ) -> AssembledContext:
        """Build a list of messages suitable for an LLM request."""
        messages: list[dict[str, Any]] = []
        rag_sources: list[str] = []

        # ── 1. System prompt ──────────────────────────────────────────
        system_content = self._build_system(
            system_prompt,
            agent_config=agent_config,
        )

        # ── 2. Long-term memory ──────────────────────────────────────
        memory_block = self._format_long_term_memories(long_term_memories)
        if memory_block:
            system_content += f"\n\n## Customer Context\n{memory_block}"

        # ── 3. RAG knowledge ─────────────────────────────────────────
        rag_block, rag_sources = self._format_rag_results(rag_results)
        if rag_block:
            system_content += f"\n\n## Knowledge Base\n{rag_block}"

        # ── 4. Session state ─────────────────────────────────────────
        session_block = self._format_session(session_memories)
        if session_block:
            system_content += f"\n\n## Session State\n{session_block}"

        messages.append({"role": "system", "content": system_content})

        # ── 5. Conversation history ──────────────────────────────────
        history_msgs = self._format_history(conversation_history, max_history_turns)
        messages.extend(history_msgs)

        # ── Token estimate ───────────────────────────────────────────
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        token_estimate = total_chars // self._CHARS_PER_TOKEN

        # If over budget, trim history (keep system + last N turns)
        if token_estimate > max_context_tokens and len(history_msgs) > 4:
            while token_estimate > max_context_tokens and len(messages) > 3:
                # Remove the oldest non-system message
                removed = messages.pop(1)
                total_chars -= len(str(removed.get("content", "")))
                token_estimate = total_chars // self._CHARS_PER_TOKEN

        return AssembledContext(
            messages=messages,
            token_estimate=token_estimate,
            rag_sources=rag_sources,
        )

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system(
        system_prompt: str,
        agent_config: Any | None = None,
    ) -> str:
        lines = [system_prompt.strip()]

        # Add global instructions
        lines.append(
            "\n## Guidelines\n"
            "- Be concise and helpful.\n"
            "- If you do not know the answer, say so honestly.\n"
            "- Only use tools when necessary and explain actions to the customer.\n"
            "- Never fabricate information not grounded in the provided context.\n"
            f"- Current UTC time: {datetime.utcnow().isoformat()}"
        )
        return "\n".join(lines)

    @staticmethod
    def _format_long_term_memories(
        memories: Sequence[CustomerMemory] | None,
    ) -> str:
        if not memories:
            return ""
        parts: list[str] = []
        for mem in memories:
            label = mem.memory_type.value if hasattr(mem.memory_type, "value") else str(mem.memory_type)
            parts.append(f"- [{label}] {mem.content}")
        return "\n".join(parts)

    @staticmethod
    def _format_rag_results(
        results: list[RAGChunk] | None,
    ) -> tuple[str, list[str]]:
        if not results:
            return "", []
        parts: list[str] = []
        sources: list[str] = []
        for idx, chunk in enumerate(results, 1):
            parts.append(f"[Source {idx}]: {chunk.content}")
            if chunk.source:
                sources.append(chunk.source)
        block = (
            "Use the following knowledge to answer the customer's question. "
            "Cite source numbers when referencing specific information.\n\n"
            + "\n\n".join(parts)
        )
        return block, sources

    @staticmethod
    def _format_session(
        session_data: dict[str, Any] | None,
    ) -> str:
        if not session_data:
            return ""
        parts: list[str] = []
        for key, value in session_data.items():
            parts.append(f"- {key}: {value}")
        return "\n".join(parts)

    @staticmethod
    def _format_history(
        history: Sequence[Message] | list[dict[str, Any]],
        max_turns: int,
    ) -> list[dict[str, Any]]:
        """Convert ORM Message objects or raw dicts to LLM message format."""
        messages: list[dict[str, Any]] = []

        raw_list: list[dict[str, Any]] = []
        for item in history:
            if isinstance(item, dict):
                raw_list.append(item)
            else:
                # ORM Message object
                role_value = item.role.value if hasattr(item.role, "value") else str(item.role)
                msg: dict[str, Any] = {
                    "role": role_value if role_value != "customer" else "user",
                    "content": item.content or "",
                }
                # Carry tool_call metadata if present
                if item.tool_call_id:
                    msg["tool_call_id"] = item.tool_call_id
                if item.tool_name:
                    msg["name"] = item.tool_name
                raw_list.append(msg)

        # Take the last N turns
        trimmed = raw_list[-max_turns:] if len(raw_list) > max_turns else raw_list
        messages.extend(trimmed)
        return messages
