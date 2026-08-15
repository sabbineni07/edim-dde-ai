"""Built-in web-search providers."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from edim_dde_ai.web.models import WebSearchRequest, WebSearchResult


class NullWebSearch:
    """Null Object used when online search is not configured."""

    name = "none"

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        del request
        return []


@dataclass
class MemoryWebSearch:
    """Deterministic provider for tests and host-supplied fixtures."""

    results: list[WebSearchResult] = field(default_factory=list)
    name: str = "memory"
    requests: list[WebSearchRequest] = field(default_factory=list)

    def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
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

    Request: ``GET endpoint?q=<query>&count=<top_k>``.
    Response may be ``{"results": [...]}``, ``{"webPages":{"value":[...]}}``
    (Bing-compatible), or a top-level list. Result fields accepted are
    ``title|name``, ``url``, and ``snippet|description``.
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
