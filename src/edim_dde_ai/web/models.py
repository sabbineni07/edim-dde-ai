"""Backend-neutral web-search request and result models.

These dataclasses are the only shapes graph nodes and providers exchange.
Providers must normalize vendor JSON into ``WebSearchResult`` so agents stay
vendor-agnostic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WebSearchRequest:
    """One bounded public-web query issued by a graph node.

    Attributes:
        query: Already-sanitized search text (domain responsibility).
        top_k: Max results to return after provider normalization.
        domains: Optional hostname allowlist; empty means provider default /
            no extra filter (builtin node may still apply its own allowlist).
    """

    query: str
    top_k: int = 5
    domains: tuple[str, ...] = ()


@dataclass
class WebSearchResult:
    """Normalized search result returned to graph nodes / prompts.

    Attributes:
        title: Page or document title.
        url: Absolute http(s) URL (citations must use this exact string).
        snippet: Short excerpt (providers should truncate ~1k chars).
        score: Optional relevance score from the backend.
        metadata: Escape hatch for provider-specific fields.
    """

    title: str
    url: str
    snippet: str = ""
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for state / API projection (``web_search_hits``)."""
        return asdict(self)
