"""OpenAI GPT provider implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from autonomocx.core.config import get_settings
from autonomocx.core.exceptions import ExternalServiceError

from .base import BaseLLMProvider, LLMRequest, LLMResponse, ToolCall

logger = structlog.get_logger(__name__)

# Pricing per 1M tokens (input / output) as of early 2025
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-11-20": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4-turbo-2024-04-09": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
}


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI chat completions API."""

    name = "openai"

    def __init__(self, api_key: str | None = None, org_id: str | None = None) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=api_key
            or (settings.openai_api_key.get_secret_value() if settings.openai_api_key else None),
            organization=org_id or settings.openai_org_id,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )
        self._default_model = settings.openai_default_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._default_model
        kwargs = self._build_kwargs(request, model)

        start = self._now_ms()
        try:
            raw = await self._client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            logger.warning("openai_rate_limit", model=model, detail=str(exc))
            raise ExternalServiceError(
                "OpenAI rate limit exceeded. Please retry later.",
                error_code="LLM_RATE_LIMIT",
            ) from exc
        except APITimeoutError as exc:
            logger.warning("openai_timeout", model=model, detail=str(exc))
            raise ExternalServiceError(
                "OpenAI request timed out.",
                error_code="LLM_TIMEOUT",
            ) from exc
        except APIError as exc:
            logger.error(
                "openai_api_error",
                model=model,
                status=getattr(exc, "status_code", None),
                detail=str(exc),
            )
            raise ExternalServiceError(
                f"OpenAI API error: {exc.message}",
                error_code="LLM_API_ERROR",
            ) from exc
        latency = self._now_ms() - start

        choice = raw.choices[0]
        tool_calls = self._parse_tool_calls(choice.message)
        usage = raw.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = self.estimate_cost(prompt_tokens, completion_tokens, model)

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            model=raw.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
            cost_usd=cost,
            request_id=request.request_id,
            finish_reason=choice.finish_reason or "",
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        model = request.model or self._default_model
        kwargs = self._build_kwargs(request, model, stream=True)

        try:
            response = await self._client.chat.completions.create(**kwargs)
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except APIError as exc:
            logger.error("openai_stream_error", model=model, detail=str(exc))
            raise ExternalServiceError(
                f"OpenAI streaming error: {exc.message}",
                error_code="LLM_STREAM_ERROR",
            ) from exc

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        pricing = _PRICING.get(model, _PRICING.get("gpt-4o", (2.50, 10.00)))
        input_cost = (input_tokens / 1_000_000) * pricing[0]
        output_cost = (output_tokens / 1_000_000) * pricing[1]
        return round(input_cost + output_cost, 8)

    def supports_tools(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_kwargs(
        self,
        request: LLMRequest,
        model: str,
        stream: bool = False,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream or request.stream,
        }
        if request.tools:
            kwargs["tools"] = request.tools
            kwargs["tool_choice"] = "auto"
        return kwargs

    @staticmethod
    def _parse_tool_calls(message: Any) -> list[ToolCall] | None:
        if not message.tool_calls:
            return None
        calls: list[ToolCall] = []
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                )
            )
        return calls
