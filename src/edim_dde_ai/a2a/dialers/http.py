"""HTTP dialer for remote ``POST /api/v1/agents/{id}/invoke`` (ADR-001 Phase 4)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from edim_dde_ai.a2a.dialers.base import DialerError


class HttpDialer:
    """Dial a peer runtime over HTTP using the Phase 3 invoke contract."""

    name = "http"

    def invoke(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float = 60.0,
    ) -> dict[str, Any]:
        endpoint = str(binding.get("endpoint") or "").rstrip("/")
        if not endpoint:
            raise DialerError("HTTP dialer requires binding.endpoint")
        path = str(
            binding.get("invoke_path")
            or f"/api/v1/agents/{binding.get('agent_id')}/invoke"
        )
        if not path.startswith("/"):
            path = "/" + path
        url = f"{endpoint}{path}"
        payload = json.dumps({"input": dict(state)}).encode("utf-8")
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {}),
        }
        req = urllib.request.Request(
            url, data=payload, headers=req_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise DialerError(
                f"HTTP dial {url} failed status={exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise DialerError(f"HTTP dial {url} failed: {exc}") from exc

        if not isinstance(body, dict):
            raise DialerError(f"HTTP dial {url} returned non-object JSON")
        # Phase 3 envelope: { agent_id, request_id, state, status }
        if isinstance(body.get("state"), dict):
            return dict(body["state"])
        return dict(body)
