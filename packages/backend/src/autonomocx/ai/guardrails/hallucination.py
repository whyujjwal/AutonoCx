"""Hallucination guard -- verify that LLM claims are grounded in context."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from autonomocx.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GroundingClaim:
    """A factual claim extracted from the LLM response."""

    text: str
    is_grounded: bool
    supporting_source: str | None = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class GroundingResult:
    """Overall grounding assessment."""

    is_grounded: bool
    score: float  # 0.0 (all hallucinated) to 1.0 (fully grounded)
    claims: list[GroundingClaim] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class HallucinationGuard:
    """Verify that an LLM response is grounded in the provided context sources.

    This uses a lightweight heuristic approach:
    1. Extract factual claims from the response (sentences containing
       numbers, proper nouns, or specific assertions).
    2. For each claim, check whether key n-grams appear in any context source.
    3. Flag claims that have no supporting evidence.

    This is intentionally simpler than a model-based grounding check, to avoid
    adding another LLM call on the critical path.
    """

    def __init__(self, threshold: float | None = None) -> None:
        settings = get_settings()
        self._threshold = threshold or settings.guardrail_hallucination_threshold

    def check_grounding(
        self,
        response: str,
        context_sources: list[str],
    ) -> GroundingResult:
        """Check whether *response* is grounded in *context_sources*.

        Returns a ``GroundingResult`` with per-claim grounding status.
        """
        if not response or not response.strip():
            return GroundingResult(is_grounded=True, score=1.0)

        if not context_sources:
            # No sources to ground against -- flag as a warning
            return GroundingResult(
                is_grounded=True,
                score=0.5,
                warnings=["No context sources provided for grounding check."],
            )

        # Build a combined search corpus (lowercased)
        corpus = "\n".join(context_sources).lower()

        # Extract claims
        claims = self._extract_claims(response)
        if not claims:
            return GroundingResult(is_grounded=True, score=1.0)

        # Check each claim
        grounded_claims: list[GroundingClaim] = []
        grounded_count = 0

        for claim_text in claims:
            is_grounded, confidence, source = self._check_claim(claim_text, corpus, context_sources)
            grounded_claims.append(
                GroundingClaim(
                    text=claim_text,
                    is_grounded=is_grounded,
                    supporting_source=source,
                    confidence=confidence,
                )
            )
            if is_grounded:
                grounded_count += 1

        score = grounded_count / len(claims) if claims else 1.0
        is_grounded = score >= self._threshold

        warnings: list[str] = []
        ungrounded = [c for c in grounded_claims if not c.is_grounded]
        if ungrounded:
            warnings.append(
                f"{len(ungrounded)} of {len(claims)} claims could not be verified "
                f"against the provided context."
            )

        logger.debug(
            "grounding_check",
            total_claims=len(claims),
            grounded=grounded_count,
            score=round(score, 3),
            is_grounded=is_grounded,
        )

        return GroundingResult(
            is_grounded=is_grounded,
            score=round(score, 3),
            claims=grounded_claims,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Claim extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_claims(text: str) -> list[str]:
        """Extract sentences that contain specific factual assertions.

        We focus on sentences containing numbers, dates, proper nouns, or
        definitive language ("is", "was", "costs", "takes", etc.).
        """
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        # Patterns indicating factual claims
        factual_patterns = [
            r"\d",               # Contains numbers
            r"\$",               # Currency
            r"\b(?:is|are|was|were|costs?|takes?|requires?|includes?)\b",
            r"\b(?:always|never|every|all|none|must|guaranteed)\b",
        ]
        compiled = [re.compile(p, re.IGNORECASE) for p in factual_patterns]

        claims: list[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            # Check if sentence contains a factual assertion
            if any(pattern.search(sentence) for pattern in compiled):
                claims.append(sentence)

        return claims

    # ------------------------------------------------------------------
    # Claim verification
    # ------------------------------------------------------------------

    def _check_claim(
        self,
        claim: str,
        corpus: str,
        sources: list[str],
    ) -> tuple[bool, float, str | None]:
        """Check if a claim is supported by any context source.

        Returns (is_grounded, confidence, supporting_source_snippet).
        """
        claim_lower = claim.lower()

        # Extract key n-grams (2-grams and 3-grams) from the claim
        words = re.findall(r"\b\w+\b", claim_lower)
        if len(words) < 2:
            return True, 0.5, None

        # Generate bigrams and trigrams
        bigrams = [" ".join(words[i : i + 2]) for i in range(len(words) - 1)]
        trigrams = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]

        # Count how many n-grams appear in the corpus
        bigram_hits = sum(1 for bg in bigrams if bg in corpus)
        trigram_hits = sum(1 for tg in trigrams if tg in corpus)

        total_ngrams = len(bigrams) + len(trigrams)
        if total_ngrams == 0:
            return True, 0.5, None

        # Weight trigram hits more heavily
        weighted_hits = bigram_hits + (trigram_hits * 2)
        weighted_total = len(bigrams) + (len(trigrams) * 2)
        match_ratio = weighted_hits / weighted_total if weighted_total > 0 else 0.0

        # Find supporting source
        supporting_source: str | None = None
        if match_ratio > 0:
            for source in sources:
                source_lower = source.lower()
                if any(tg in source_lower for tg in trigrams):
                    # Return a snippet
                    for tg in trigrams:
                        idx = source_lower.find(tg)
                        if idx >= 0:
                            start = max(0, idx - 40)
                            end = min(len(source), idx + len(tg) + 40)
                            supporting_source = source[start:end]
                            break
                    break

        # Threshold for considering a claim grounded
        is_grounded = match_ratio >= 0.3
        confidence = min(match_ratio * 1.5, 1.0)

        return is_grounded, round(confidence, 3), supporting_source
