"""Retrieval hit and search request models (backend-agnostic)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RetrievalHit:
    """One ranked document/chunk from similarity or hybrid search."""

    id: str
    text: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievalHit:
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            score=float(data.get("score") or 0.0),
            metadata=dict(data.get("metadata") or {}),
            source=(str(data["source"]) if data.get("source") is not None else None),
        )


@dataclass
class SearchRequest:
    """Normalized search request passed to every RetrievalProvider."""

    query: str
    corpus: str = "default"
    top_k: int = 5
    search_mode: str = "hybrid"  # vector | keyword | hybrid
    filters: dict[str, Any] = field(default_factory=dict)


def format_hits_as_context(
    hits: list[RetrievalHit], *, max_chars: int = 8000
) -> str:
    """Render hits for LLM prompt injection (RAG context block)."""
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
