"""Strategy protocol for pluggable public-web search backends.

Hosts inject a concrete ``WebSearchProvider`` at process start
(``configure_web_search_from_env`` or ``set_web_search_provider``). Graph nodes
depend only on this protocol so unit tests can swap in ``MemoryWebSearch``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.web.models import WebSearchRequest, WebSearchResult


@runtime_checkable
class WebSearchProvider(Protocol):
    """Process-wide strategy for bounded public-web search.

    Implementations must be safe to call from request threads, return quickly
    (or honor their own timeouts), and never raise for "no results" — empty
    lists are success. Transport failures may raise; the builtin ``web.search``
    node catches and fail-opens.
    """

    @property
    def name(self) -> str:
        """Short backend id for health checks (``none``, ``memory``, ``http_json``)."""
        ...

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Return score-ordered, normalized results for ``request.query``.

        Args:
            request: Sanitized query + ``top_k`` + optional domain filter.

        Returns:
            Zero or more ``WebSearchResult`` rows, already truncated to
            ``top_k`` when possible.
        """
        ...
