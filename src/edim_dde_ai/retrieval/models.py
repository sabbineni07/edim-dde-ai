"""Backend-agnostic retrieval hit and search request models.

Business purpose
----------------
Every ``RetrievalProvider`` speaks the same request/response shapes so graph
nodes and prompt formatters stay backend-agnostic. Hits are also the input to
``experiences.dedupe.dedupe_retrieval_hits`` before LLM context injection.

Public API
----------
* ``RetrievalHit`` — one ranked chunk (``to_dict`` / ``from_dict``)
* ``SearchRequest`` — normalized search args
* ``format_hits_as_context`` — render hits for RAG prompt blocks
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RetrievalHit:
    """One ranked document/chunk from similarity or hybrid search.

    Attributes:
        id: Stable document/chunk id within the corpus.
        text: Body text injected into prompts.
        score: Backend similarity / relevance score (higher is better).
        metadata: Opaque provider fields (paths, action signatures, etc.).
        source: Optional origin label (file path, URI).
    """

    id: str
    text: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-friendly).

        Returns:
            Field mapping suitable for logs, caches, or wire payloads.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievalHit:
        """Build a hit from a dict (tolerant of missing keys).

        Args:
            data: Mapping with optional ``id``, ``text``, ``score``,
                ``metadata``, ``source``.

        Returns:
            Normalized ``RetrievalHit`` (empty strings / 0.0 when absent).
        """
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            score=float(data.get("score") or 0.0),
            metadata=dict(data.get("metadata") or {}),
            source=(str(data["source"]) if data.get("source") is not None else None),
        )


@dataclass
class SearchRequest:
    """Normalized search request passed to every ``RetrievalProvider``.

    Attributes:
        query: Natural-language or keyword query string.
        corpus: Logical corpus name (default ``default``).
        top_k: Maximum hits to return.
        search_mode: ``vector`` | ``keyword`` | ``hybrid`` (provider-dependent).
        filters: Optional backend-specific filter map.
    """

    query: str
    corpus: str = "default"
    top_k: int = 5
    search_mode: str = "hybrid"  # vector | keyword | hybrid
    filters: dict[str, Any] = field(default_factory=dict)


def format_hits_as_context(
    hits: list[RetrievalHit], *, max_chars: int = 8000
) -> str:
    """Render hits for LLM prompt injection (RAG context block).

    Stops adding chunks once the next chunk would exceed ``max_chars``.

    Args:
        hits: Ranked retrieval results (already truncated/deduped by caller).
        max_chars: Soft character budget for the assembled context string.

    Returns:
        Multi-hit text block, or a fixed placeholder when ``hits`` is empty.

    Example::

        ctx = format_hits_as_context(hits, max_chars=4000)
        prompt = f"Use these runbooks:\\n{ctx}\\n\\nQuestion: ..."
    """
    if not hits:
        return "(no runbook / knowledge hits retrieved)"
    parts: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        header = f"[{i}] id={hit.id} score={hit.score:.4f}"
        if hit.source:
            header += f" source={hit.source}"
        chunk = f"{header}\n{hit.text.strip()}"
        if used + len(chunk) + 2 > max_chars:
            break
        parts.append(chunk)
        used += len(chunk) + 2
    return "\n\n".join(parts)
