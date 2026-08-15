"""Process-wide web-search provider registry and environment factory."""

from __future__ import annotations

import os

from edim_dde_ai.web.protocols import WebSearchProvider
from edim_dde_ai.web.providers import HttpJsonWebSearch, NullWebSearch

_PROVIDER: WebSearchProvider = NullWebSearch()


def set_web_search_provider(provider: WebSearchProvider) -> None:
    global _PROVIDER
    _PROVIDER = provider


def get_web_search_provider() -> WebSearchProvider:
    return _PROVIDER


def configure_web_search_from_env() -> WebSearchProvider:
    """Configure ``none`` or host-managed ``http_json`` search."""
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
