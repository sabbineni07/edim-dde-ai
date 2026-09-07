"""Correlation helpers for nested ``invoke_agent`` hops (ADR-001 Phase 1)."""

from __future__ import annotations

import uuid
from typing import Any

from edim_dde_ai.observability.base import build_run_config


def child_correlation(
    parent_state: dict[str, Any],
    *,
    child_agent_id: str,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    """Build LangGraph config, HTTP headers, and state correlation fields.

    Returns:
        ``(config, headers, state_extras)`` where ``state_extras`` should be
        merged into the child input so flat state carries the same ids.
    """
    request_id = str(parent_state.get("request_id") or "").strip() or str(uuid.uuid4())
    parent_span = str(parent_state.get("span_id") or "").strip()
    span_id = str(uuid.uuid4())
    depth = int(parent_state.get("invoke_depth") or 0) + 1
    config = build_run_config(
        agent_id=child_agent_id,
        request_id=request_id,
        metadata={
            "span_id": span_id,
            "parent_span_id": parent_span or None,
            "invoke_depth": depth,
        },
    )
    headers = {
        "X-Request-Id": request_id,
        "X-Edim-Span-Id": span_id,
        "X-Edim-Invoke-Depth": str(depth),
    }
    if parent_span:
        headers["X-Edim-Parent-Span-Id"] = parent_span
    extras = {
        "request_id": request_id,
        "span_id": span_id,
        "invoke_depth": depth,
    }
    if parent_span:
        extras["parent_span_id"] = parent_span
    return config, headers, extras
