"""Backend-neutral web-search request and result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WebSearchRequest:
    """One bounded public-web query."""

    query: str
    top_k: int = 5
    domains: tuple[str, ...] = ()


@dataclass
class WebSearchResult:
    """Normalized search result returned to graph nodes."""

    title: str
    url: str
    snippet: str = ""
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
