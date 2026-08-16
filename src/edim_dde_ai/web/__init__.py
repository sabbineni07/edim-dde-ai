"""Optional, pluggable public-web search capability (framework layer).

Business purpose
----------------
Agents (today: ``spark_rca``) may enrich prompts with bounded public-web hits
when YAML enables it. This package is the **provider seam** — domain agents
never call Bing/Google SDKs directly.

Layers
------
* ``models`` — ``WebSearchRequest`` / ``WebSearchResult``
* ``protocols`` — ``WebSearchProvider`` strategy interface
* ``providers`` — ``none`` / ``memory`` / ``http_json`` implementations
* ``registry`` — process-wide get/set + ``EDIM_WEB_SEARCH`` env factory

Builtin graph node ``web.search`` (in ``edim_dde_ai.nodes.builtin``) reads the
registry, allowlists domains, and fail-opens to empty hits on provider errors.

Security notes
--------------
Domain agents must sanitize queries **before** calling search (exception-class
tokens only). This package does not redact PII itself.
"""

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
