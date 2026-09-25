"""HTTP dialer for remote ``POST /api/v1/agents/{id}/invoke`` (ADR-001 / ADR-002).

Hardening:
  * ``EDIM_A2A_HTTP_TIMEOUT_S`` (default 60)
  * ``EDIM_A2A_HTTP_RETRIES`` (default 2) on 502/503/504 and transport errors
  * ``EDIM_A2A_TOKEN`` → ``Authorization: Bearer …`` when set (A2A AuthZ)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from edim_dde_ai.a2a.dialers.base import DialerError

logger = logging.getLogger(__name__)

ENV_TIMEOUT = "EDIM_A2A_HTTP_TIMEOUT_S"
ENV_RETRIES = "EDIM_A2A_HTTP_RETRIES"
ENV_A2A_TOKEN = "EDIM_A2A_TOKEN"

_RETRYABLE_STATUS = frozenset({502, 503, 504})


def _timeout_s(explicit: float | None = None) -> float:
    if explicit is not None:
        return float(explicit)
    raw = (os.environ.get(ENV_TIMEOUT) or "60").strip()
    try:
        value = float(raw)
    except ValueError:
        return 60.0
    return value if value > 0 else 60.0


def _max_attempts() -> int:
    raw = (os.environ.get(ENV_RETRIES) or "2").strip()
    try:
        retries = int(raw)
    except ValueError:
        retries = 2
    return max(1, retries + 1)  # attempts = 1 + retries


def _auth_headers() -> dict[str, str]:
    token = (os.environ.get(ENV_A2A_TOKEN) or "").strip()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "X-Edim-A2A-Token": token,
    }


class HttpDialer:
    """Dial a peer runtime over HTTP using the ADR-002 invoke contract."""

    name = "http"

    def invoke_envelope(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """POST invoke and return the full ADR-002 envelope."""
        from edim_dde_ai.a2a.envelope import parse_call_envelope

        body = self._post_json(binding, state, headers=headers, timeout_s=timeout_s)
        return parse_call_envelope(body)

    def invoke(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """POST invoke; return flat child ``state`` (legacy subgraph dial path)."""
        body = self._post_json(binding, state, headers=headers, timeout_s=timeout_s)
        if isinstance(body.get("state"), dict):
            return dict(body["state"])
        return dict(body)

    def _post_json(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
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
        cid = str(state.get("conversation_id") or state.get("thread_id") or "").strip()
        body_obj: dict[str, Any] = {"input": dict(state)}
        if cid:
            body_obj["conversation_id"] = cid
        if state.get("a2a_async"):
            body_obj["async_accept"] = True
        payload = json.dumps(body_obj).encode("utf-8")
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **_auth_headers(),
            **(headers or {}),
        }
        timeout = _timeout_s(timeout_s)
        attempts = _max_attempts()
        last_exc: BaseException | None = None

        for attempt in range(1, attempts + 1):
            req = urllib.request.Request(
                url, data=payload, headers=req_headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    body = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                if exc.code in _RETRYABLE_STATUS and attempt < attempts:
                    logger.warning(
                        "HTTP dial retryable status=%s attempt=%s/%s url=%s",
                        exc.code,
                        attempt,
                        attempts,
                        url,
                    )
                    time.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
                    last_exc = DialerError(
                        f"HTTP dial {url} failed status={exc.code}: {detail}"
                    )
                    continue
                raise DialerError(
                    f"HTTP dial {url} failed status={exc.code}: {detail}"
                ) from exc
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
            ) as exc:
                if attempt < attempts:
                    logger.warning(
                        "HTTP dial transport error attempt=%s/%s url=%s err=%s",
                        attempt,
                        attempts,
                        url,
                        exc,
                    )
                    time.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
                    last_exc = DialerError(f"HTTP dial {url} failed: {exc}")
                    continue
                raise DialerError(f"HTTP dial {url} failed: {exc}") from exc

            if not isinstance(body, dict):
                raise DialerError(f"HTTP dial {url} returned non-object JSON")
            return body

        raise last_exc or DialerError(
            f"HTTP dial {url} failed after {attempts} attempts"
        )
