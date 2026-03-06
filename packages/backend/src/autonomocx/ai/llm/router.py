"""Multi-LLM router that picks the best provider per request."""

from __future__ import annotations

from typing import Any

import structlog

from .base import BaseLLMProvider, LLMRequest, LLMResponse
from .fallback import FallbackChain

logger = structlog.get_logger(__name__)


class LLMRouter:
    """Routes LLM requests based on agent config, task type, cost, and latency.

    Strategy priority:
    1. **Agent override** -- if ``agent_config`` specifies a provider/model, honour it.
    2. **Task routing** -- requests with tools go to the best tool-calling provider;
       simple completions route to the cheapest suitable model.
    3. **Cost optimisation** -- estimate tokens and compare projected cost.
    4. **Fallback** -- if the primary provider fails, the fallback chain handles retries
       across remaining providers.
    """

    def __init__(self, providers: dict[str, BaseLLMProvider]) -> None:
        self._providers = providers
        self._fallback_chain = FallbackChain(providers=list(providers.values()))

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def route(
        self,
        request: LLMRequest,
        agent_config: Any | None = None,
    ) -> LLMResponse:
        """Determine the best provider and execute the request."""

        # 1. Agent-level override
        provider_name, model = self._resolve_agent_override(agent_config)

        if provider_name and provider_name in self._providers:
            if model:
                request.model = model
            provider = self._providers[provider_name]
            logger.debug(
                "llm_route_agent_override",
                provider=provider_name,
                model=request.model,
            )
            try:
                return await provider.complete(request)
            except Exception:
                logger.warning(
                    "llm_route_agent_override_failed",
                    provider=provider_name,
                    model=request.model,
                )
                return await self._fallback(request, exclude={provider_name})

        # 2. Task-based routing
        provider = self._select_by_task(request)
        if model:
            request.model = model
        logger.debug(
            "llm_route_task",
            provider=provider.name,
            model=request.model,
            has_tools=bool(request.tools),
        )

        try:
            return await provider.complete(request)
        except Exception:
            logger.warning(
                "llm_route_primary_failed",
                provider=provider.name,
            )
            return await self._fallback(request, exclude={provider.name})

    async def route_stream(
        self,
        request: LLMRequest,
        agent_config: Any | None = None,
    ):
        """Route and stream the response.  Returns an async iterator of deltas."""

        provider_name, model = self._resolve_agent_override(agent_config)
        if provider_name and provider_name in self._providers:
            provider = self._providers[provider_name]
        else:
            provider = self._select_by_task(request)

        if model:
            request.model = model
        request.stream = True

        async for delta in provider.stream(request):
            yield delta

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    async def _fallback(self, request: LLMRequest, exclude: set[str]) -> LLMResponse:
        """Try remaining providers via the fallback chain."""
        return await self._fallback_chain.call(request, exclude=exclude)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_agent_override(agent_config: Any | None) -> tuple[str | None, str | None]:
        """Extract provider and model from agent config if present."""
        if agent_config is None:
            return None, None

        provider = getattr(agent_config, "llm_provider", None)
        model = getattr(agent_config, "llm_model", None)
        return provider, model

    def _select_by_task(self, request: LLMRequest) -> BaseLLMProvider:
        """Pick a provider based on request characteristics."""

        # If tools are requested, prefer a provider that supports them
        if request.tools:
            for provider in self._providers.values():
                if provider.supports_tools():
                    return provider

        # Prefer cheapest provider for simple completions
        # (heuristic: pick the first available -- ordering is set at init time)
        return next(iter(self._providers.values()))
