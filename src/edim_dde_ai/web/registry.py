"""Process-wide web-search provider registry and environment factory.

Business purpose
----------------
One provider per process (same pattern as RecommendationStore / Retrieval).
API lifespan calls ``configure_web_search_from_env()``; tests call
``set_web_search_provider(MemoryWebSearch(...))``.

Env vars
--------
* ``EDIM_WEB_SEARCH`` — ``none`` (default) | ``http_json``
* ``EDIM_WEB_SEARCH_ENDPOINT`` — HTTPS gateway URL (required for http_json)
* ``EDIM_WEB_SEARCH_API_KEY`` — optional
* ``EDIM_WEB_SEARCH_TIMEOUT_SECONDS`` — default ``8``
* ``EDIM_WEB_SEARCH_KEY_HEADER`` — default Bing-style subscription header
"""

from __future__ import annotations

import os

from edim_dde_ai.web.protocols import WebSearchProvider
from edim_dde_ai.web.providers import HttpJsonWebSearch, NullWebSearch

_PROVIDER: WebSearchProvider = NullWebSearch()


def set_web_search_provider(provider: WebSearchProvider) -> None:
    """Replace the process-wide provider (tests / custom host wiring).

    Args:
        provider: Any object satisfying ``WebSearchProvider``.
    """
    global _PROVIDER
    _PROVIDER = provider


def get_web_search_provider() -> WebSearchProvider:
    """Return the current process-wide provider (never ``None``)."""
    return _PROVIDER


def configure_web_search_from_env() -> WebSearchProvider:
    """Configure ``none`` or host-managed ``http_json`` search from the environment.

    Returns:
        The provider that was installed (also available via
        ``get_web_search_provider``).

    Raises:
        ValueError: Unknown ``EDIM_WEB_SEARCH`` backend or invalid http_json
            endpoint (propagated from ``HttpJsonWebSearch``).
    """
    backend = os.getenv("EDIM_WEB_SEARCH", "none").strip().lower()
    if backend in {"", "none", "off", "disabled"}:
        provider: WebSearchProvider = NullWebSearch()
    elif backend == "http_json":
        provider = HttpJsonWebSearch(
            endpoint=os.getenv("EDIM_WEB_SEARCH_ENDPOINT", ""),
            api_key=os.getenv("EDIM_WEB_SEARCH_API_KEY", ""),
            timeout_seconds=float(os.getenv("EDIM_WEB_SEARCH_TIMEOUT_SECONDS", "8")),
            key_header=os.getenv(
                "EDIM_WEB_SEARCH_KEY_HEADER", "Ocp-Apim-Subscription-Key"
            ),
        )
    else:
        raise ValueError(
            f"Unknown EDIM_WEB_SEARCH backend {backend!r}; expected none|http_json"
        )
    set_web_search_provider(provider)
    return provider
