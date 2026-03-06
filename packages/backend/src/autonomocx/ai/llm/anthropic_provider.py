"""Anthropic Claude provider implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from anthropic import APIError, APITimeoutError, AsyncAnthropic, RateLimitError

from autonomocx.core.config import get_settings
from autonomocx.core.exceptions import ExternalServiceError

from .base import BaseLLMProvider, LLMRequest, LLMResponse, ToolCall

logger = structlog.get_logger(__name__)

# Pricing per 1M tokens (input / output)
_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-haiku-3-5-20241022": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
}


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(
            api_key=api_key
            or (
                settings.anthropic_api_key.get_secret_value()
                if settings.anthropic_api_key
                else None
            ),
            timeout=settings.anthropic_timeout,
            max_retries=settings.anthropic_max_retries,
        )
        self._default_model = settings.anthropic_default_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._default_model
        kwargs = self._build_kwargs(request, model)

        start = self._now_ms()
        try:
            raw = await self._client.messages.create(**kwargs)
        except RateLimitError as exc:
            logger.warning("anthropic_rate_limit", model=model, detail=str(exc))
            raise ExternalServiceError(
                "Anthropic rate limit exceeded. Please retry later.",
                error_code="LLM_RATE_LIMIT",
            ) from exc
        except APITimeoutError as exc:
            logger.warning("anthropic_timeout", model=model, detail=str(exc))
            raise ExternalServiceError(
                "Anthropic request timed out.",
                error_code="LLM_TIMEOUT",
            ) from exc
        except APIError as exc:
            logger.error(
                "anthropic_api_error",
                model=model,
                status=getattr(exc, "status_code", None),
                detail=str(exc),
            )
            raise ExternalServiceError(
                f"Anthropic API error: {exc}",
                error_code="LLM_API_ERROR",
            ) from exc
        latency = self._now_ms() - start

        # Parse content blocks
        content_text = ""
        tool_calls: list[ToolCall] = []
        for block in raw.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        usage = raw.usage
        prompt_tokens = usage.input_tokens
        completion_tokens = usage.output_tokens
        cost = self.estimate_cost(prompt_tokens, completion_tokens, model)

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls if tool_calls else None,
            model=raw.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
            cost_usd=cost,
            request_id=request.request_id,
            finish_reason=raw.stop_reason or "",
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        model = request.model or self._default_model
        kwargs = self._build_kwargs(request, model)

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except APIError as exc:
            logger.error("anthropic_stream_error", model=model, detail=str(exc))
            raise ExternalServiceError(
                f"Anthropic streaming error: {exc}",
                error_code="LLM_STREAM_ERROR",
            ) from exc

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        pricing = _PRICING.get(model, (3.00, 15.00))
        input_cost = (input_tokens / 1_000_000) * pricing[0]
        output_cost = (output_tokens / 1_000_000) * pricing[1]
        return round(input_cost + output_cost, 8)

    def supports_tools(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_kwargs(self, request: LLMRequest, model: str) -> dict[str, Any]:
        # Anthropic separates system from user/assistant messages
        system_content = ""
        non_system_messages: list[dict[str, Any]] = []

        for msg in request.messages:
            if msg.get("role") == "system":
                system_content += msg.get("content", "") + "\n"
            elif msg.get("role") == "tool":
                # Convert OpenAI tool result format to Anthropic format
                non_system_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.get("tool_call_id", ""),
                                "content": msg.get("content", ""),
                            }
                        ],
                    }
                )
            elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Convert assistant message with tool_calls to Anthropic format
                content_blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"])
                            if isinstance(tc["function"]["arguments"], str)
                            else tc["function"]["arguments"],
                        }
                    )
                non_system_messages.append(
                    {
                        "role": "assistant",
                        "content": content_blocks,
                    }
                )
            else:
                non_system_messages.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": non_system_messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        system_content = system_content.strip()
        if system_content:
            kwargs["system"] = system_content

        if request.tools:
            kwargs["tools"] = self._convert_tools(request.tools)

        return kwargs

    @staticmethod
    def _convert_tools(openai_tools: list[dict]) -> list[dict[str, Any]]:
        """Convert OpenAI function-calling tool format to Anthropic tool format."""
        anthropic_tools: list[dict[str, Any]] = []
        for tool in openai_tools:
            func = tool.get("function", tool)
            anthropic_tools.append(
                {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return anthropic_tools
