"""Built-in web-search providers (null / memory / host-managed HTTP JSON).

Business purpose
----------------
Concrete strategies behind ``WebSearchProvider``. Production hosts typically
run ``HttpJsonWebSearch`` against an approved corporate search gateway
(``EDIM_WEB_SEARCH=http_json``). Tests use ``MemoryWebSearch``. Default /
disabled is ``NullWebSearch`` (empty results, never raises).

Security
--------
``HttpJsonWebSearch`` requires ``https://`` endpoints. API keys travel only in
configured headers. Domain filtering is applied in ``MemoryWebSearch`` and
usually again in the builtin ``web.search`` node.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from edim_dde_ai.web.models import WebSearchRequest, WebSearchResult


class NullWebSearch:
    """Null Object used when online search is not configured.

    Always returns ``[]``. Safe default for local/dev and when
    ``EDIM_WEB_SEARCH=none``.
    """

    name = "none"

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Ignore the request and return no hits."""
        del request
        return []


@dataclass
class MemoryWebSearch:
    """Deterministic provider for tests and host-supplied fixtures.

    Attributes:
        results: Preloaded hits returned (optionally domain-filtered).
        name: Registry/health label (default ``memory``).
        requests: Append-only log of calls (useful in unit tests).
    """

    results: list[WebSearchResult] = field(default_factory=list)
    name: str = "memory"
    requests: list[WebSearchRequest] = field(default_factory=list)

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Record ``request`` and return up to ``top_k`` domain-filtered rows."""
        self.requests.append(request)
        allowed = {d.lower() for d in request.domains}
        rows = self.results
        if allowed:
            rows = [
                row
                for row in rows
                if (urllib.parse.urlparse(row.url).hostname or "").lower() in allowed
            ]
        return rows[: max(1, request.top_k)]


class HttpJsonWebSearch:
    """Adapter for a host-managed JSON search endpoint.

    Request: ``GET endpoint?q=<query>&count=<top_k>`` (and optional ``domains``).
    Response may be ``{\"results\": [...]}``, ``{\"webPages\":{\"value\":[...]}}``
    (Bing-compatible), or a top-level list. Result fields accepted are
    ``title|name``, ``url``, and ``snippet|description``.

    Args:
        endpoint: Full HTTPS URL of the gateway (query string appended).
        api_key: Optional subscription key.
        timeout_seconds: urllib timeout (minimum 0.5s).
        key_header: Header name for ``api_key`` (Bing-style default).

    Raises:
        ValueError: If endpoint is not ``https://``.
        RuntimeError: On transport / JSON failures (caller may fail-open).
    """

    name = "http_json"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str = "",
        timeout_seconds: float = 8.0,
        key_header: str = "Ocp-Apim-Subscription-Key",
    ) -> None:
        self._endpoint = endpoint.strip()
        self._api_key = api_key.strip()
        self._timeout = max(0.5, float(timeout_seconds))
        self._key_header = key_header.strip() or "Ocp-Apim-Subscription-Key"
        if not self._endpoint.lower().startswith("https://"):
            raise ValueError("EDIM_WEB_SEARCH_ENDPOINT must use https://")

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """GET the gateway and normalize the JSON payload into results."""
        params = {"q": request.query, "count": str(max(1, request.top_k))}
        if request.domains:
            params["domains"] = ",".join(request.domains)
        separator = "&" if "?" in self._endpoint else "?"
        url = self._endpoint + separator + urllib.parse.urlencode(params)
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers[self._key_header] = self._api_key
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"web search request failed: {type(exc).__name__}") from exc
        return self._normalize(payload, request.top_k)

    @staticmethod
    def _normalize(payload: Any, top_k: int) -> list[WebSearchResult]:
        """Map heterogeneous vendor JSON into ``WebSearchResult`` rows."""
        rows: Any = payload
        if isinstance(payload, dict):
            rows = payload.get("results")
            if rows is None:
                rows = (payload.get("webPages") or {}).get("value")
            if rows is None:
                rows = payload.get("items")
        if not isinstance(rows, list):
            return []
        out: list[WebSearchResult] = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("url") or raw.get("link") or "").strip()
            if not url.lower().startswith(("https://", "http://")):
                continue
            score: float | None = None
            try:
                if raw.get("score") is not None:
                    score = float(raw["score"])
            except (TypeError, ValueError):
                pass
            out.append(
                WebSearchResult(
                    title=str(raw.get("title") or raw.get("name") or url).strip(),
                    url=url,
                    snippet=str(
                        raw.get("snippet") or raw.get("description") or ""
                    ).strip()[:1200],
                    score=score,
                )
            )
        return out[: max(1, top_k)]
