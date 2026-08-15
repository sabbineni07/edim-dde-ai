"""Strategy protocol for pluggable public-web search backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.web.models import WebSearchRequest, WebSearchResult


@runtime_checkable
class WebSearchProvider(Protocol):
    @property
    def name(self) -> str: ...

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Return score-ordered, normalized results."""
