"""Optional, pluggable public-web search capability."""

from edim_dde_ai.web.models import WebSearchRequest, WebSearchResult
from edim_dde_ai.web.protocols import WebSearchProvider
from edim_dde_ai.web.providers import HttpJsonWebSearch, MemoryWebSearch, NullWebSearch
from edim_dde_ai.web.registry import (
    configure_web_search_from_env,
    get_web_search_provider,
    set_web_search_provider,
)

__all__ = [
    "WebSearchProvider",
    "WebSearchRequest",
    "WebSearchResult",
    "NullWebSearch",
    "MemoryWebSearch",
    "HttpJsonWebSearch",
    "set_web_search_provider",
    "get_web_search_provider",
    "configure_web_search_from_env",
]
