"""Document chunking with recursive paragraph/sentence splitting."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A single chunk of text after splitting."""

    id: str
    content: str
    index: int
    char_start: int
    char_end: int
    metadata: dict = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.content)


class TextChunker:
    """Recursively splits text into overlapping chunks of target size.

    Strategy:
    1. Try splitting on paragraph boundaries (``\\n\\n``).
    2. If any resulting chunk is still too large, split on single newlines.
    3. If still too large, split on sentence boundaries (``. ``).
    4. Final fallback: hard split on character count.
    """

    # Ordered list of separators from coarsest to finest
    _SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
        metadata: dict | None = None,
    ) -> list[TextChunk]:
        """Split *text* into chunks of at most *chunk_size* characters
        with *overlap* character overlap between consecutive chunks."""
        if not text or not text.strip():
            return []

        raw_chunks = self._recursive_split(text, chunk_size, separators=list(self._SEPARATORS))

        # Merge very small chunks into their predecessor
        merged = self._merge_small(raw_chunks, chunk_size)

        # Apply overlap
        overlapped = self._apply_overlap(merged, overlap, text)

        # Build TextChunk objects
        result: list[TextChunk] = []
        offset = 0
        for idx, chunk_text in enumerate(overlapped):
            # Approximate char_start by finding the chunk in the original
            start = text.find(chunk_text[:60], offset)
            if start == -1:
                start = offset
            end = start + len(chunk_text)

            result.append(
                TextChunk(
                    id=uuid.uuid4().hex,
                    content=chunk_text,
                    index=idx,
                    char_start=start,
                    char_end=end,
                    metadata=metadata or {},
                )
            )
            # Advance offset past the non-overlapping portion
            if idx < len(overlapped) - 1:
                offset = max(start + len(chunk_text) - overlap, offset + 1)

        return result

    # ------------------------------------------------------------------
    # Recursive splitting
    # ------------------------------------------------------------------

    def _recursive_split(
        self,
        text: str,
        chunk_size: int,
        separators: list[str],
    ) -> list[str]:
        """Split text using the first separator that produces useful splits.
        Recurse on any pieces that are still too large."""
        if len(text) <= chunk_size:
            return [text.strip()] if text.strip() else []

        if not separators:
            # Hard split as last resort
            return self._hard_split(text, chunk_size)

        sep = separators[0]
        remaining_seps = separators[1:]
        parts = text.split(sep)

        # If the separator didn't actually split, try the next one
        if len(parts) <= 1:
            return self._recursive_split(text, chunk_size, remaining_seps)

        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    chunks.append(current.strip())
                # If the part itself is too large, recurse with finer separators
                if len(part) > chunk_size:
                    sub_chunks = self._recursive_split(part, chunk_size, remaining_seps)
                    chunks.extend(sub_chunks)
                    current = ""
                else:
                    current = part

        if current.strip():
            chunks.append(current.strip())

        return chunks

    @staticmethod
    def _hard_split(text: str, chunk_size: int) -> list[str]:
        """Character-level split as the final fallback."""
        result: list[str] = []
        for i in range(0, len(text), chunk_size):
            piece = text[i : i + chunk_size].strip()
            if piece:
                result.append(piece)
        return result

    @staticmethod
    def _merge_small(chunks: list[str], chunk_size: int, min_frac: float = 0.15) -> list[str]:
        """Merge chunks smaller than *min_frac* of chunk_size into neighbours."""
        min_len = int(chunk_size * min_frac)
        if not chunks:
            return []

        merged: list[str] = [chunks[0]]
        for chunk in chunks[1:]:
            if len(chunk) < min_len and merged:
                # Merge into previous if combined size is acceptable
                combined = merged[-1] + "\n" + chunk
                if len(combined) <= chunk_size:
                    merged[-1] = combined
                    continue
            merged.append(chunk)
        return merged

    @staticmethod
    def _apply_overlap(chunks: list[str], overlap: int, original: str) -> list[str]:
        """Prepend overlap characters from the previous chunk's tail."""
        if overlap <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            # Only prepend if it doesn't already start with this text
            if not chunks[i].startswith(prev_tail):
                result.append(prev_tail + chunks[i])
            else:
                result.append(chunks[i])
        return result
