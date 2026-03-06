"""Fallback chain with circuit breaker and exponential backoff."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import structlog

from autonomocx.core.exceptions import ExternalServiceError

from .base import BaseLLMProvider, LLMRequest, LLMResponse

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class _CircuitState:
    """Per-provider circuit breaker state."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False

    # Thresholds
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 60.0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
            )

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False

    def should_allow(self) -> bool:
        """Return True if the circuit is closed or enough time has passed (half-open)."""
        if not self.is_open:
            return True
        elapsed = time.monotonic() - self.last_failure_time
        if elapsed >= self.recovery_timeout_seconds:
            # Half-open: allow a single probe request
            return True
        return False


@dataclass(slots=True)
class FallbackChain:
    """Try LLM providers in priority order with circuit-breaking and backoff.

    Usage::

        chain = FallbackChain(providers=[openai_provider, anthropic_provider])
        response = await chain.call(request)
    """

    providers: list[BaseLLMProvider]
    max_retries_per_provider: int = 2
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    _circuits: dict[str, _CircuitState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for provider in self.providers:
            if provider.name not in self._circuits:
                self._circuits[provider.name] = _CircuitState()

    async def call(
        self,
        request: LLMRequest,
        *,
        exclude: set[str] | None = None,
    ) -> LLMResponse:
        """Execute the request against providers in order, skipping excluded names.

        Raises ``ExternalServiceError`` if all providers fail.
        """
        exclude = exclude or set()
        errors: list[str] = []

        for provider in self.providers:
            if provider.name in exclude:
                continue

            circuit = self._circuits[provider.name]
            if not circuit.should_allow():
                logger.info(
                    "circuit_breaker_skip",
                    provider=provider.name,
                    failure_count=circuit.failure_count,
                )
                errors.append(f"{provider.name}: circuit open")
                continue

            # Retry loop for this provider
            backoff = self.initial_backoff_seconds
            for attempt in range(1, self.max_retries_per_provider + 1):
                try:
                    response = await provider.complete(request)
                    circuit.record_success()
                    if attempt > 1:
                        logger.info(
                            "fallback_retry_success",
                            provider=provider.name,
                            attempt=attempt,
                        )
                    return response
                except ExternalServiceError as exc:
                    logger.warning(
                        "fallback_attempt_failed",
                        provider=provider.name,
                        attempt=attempt,
                        error=str(exc),
                    )
                    errors.append(f"{provider.name} attempt {attempt}: {exc.message}")

                    if attempt < self.max_retries_per_provider:
                        await asyncio.sleep(backoff)
                        backoff *= self.backoff_multiplier
                except Exception as exc:
                    logger.error(
                        "fallback_unexpected_error",
                        provider=provider.name,
                        attempt=attempt,
                        error=str(exc),
                    )
                    errors.append(f"{provider.name} attempt {attempt}: {exc}")
                    break  # Don't retry on unexpected errors

            # All retries exhausted for this provider
            circuit.record_failure()

        # Every provider failed
        detail = "; ".join(errors)
        raise ExternalServiceError(
            f"All LLM providers failed: {detail}",
            error_code="LLM_ALL_PROVIDERS_FAILED",
        )
