"""LangSmith / LangChain tracing helpers (BL-029 prep)."""

from __future__ import annotations

import os
import uuid
from typing import Any


def tracing_enabled() -> bool:
    if os.environ.get("EDIM_LANGSMITH_ENABLED", "").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False
    return os.environ.get("LANGCHAIN_TRACING_V2", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_run_config(
    *,
    agent_id: str,
    request_id: str | None = None,
    extra_tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a LangGraph ``config`` dict with runnable tags/metadata.

    Safe to pass even when tracing is disabled — LangGraph ignores unused keys.
    """
    env = (os.environ.get("EDIM_ENV") or "local").strip().lower()
    rid = (request_id or "").strip() or str(uuid.uuid4())
    tags = [f"agent_id:{agent_id}", f"env:{env}"]
    if extra_tags:
        tags.extend(extra_tags)
    meta: dict[str, Any] = {
        "agent_id": agent_id,
        "edim_env": env,
        "request_id": rid,
    }
    if metadata:
        meta.update(metadata)
    return {
        "run_name": agent_id,
        "tags": tags,
        "metadata": meta,
    }


def merge_invoke_kwargs(
    agent_id: str,
    kwargs: dict[str, Any],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Merge tracing config into ``MetadataAgent.invoke`` kwargs."""
    out = dict(kwargs)
    existing = out.get("config")
    if existing is None:
        existing = {}
    elif not isinstance(existing, dict):
        return out
    built = build_run_config(
        agent_id=agent_id,
        request_id=request_id or (existing.get("metadata") or {}).get("request_id"),
    )
    merged = dict(existing)
    # Prefer caller-provided run_name/tags/metadata; fill gaps from built.
    if "run_name" not in merged:
        merged["run_name"] = built["run_name"]
    tags = list(merged.get("tags") or [])
    for t in built["tags"]:
        if t not in tags:
            tags.append(t)
    merged["tags"] = tags
    meta = dict(built["metadata"])
    meta.update(merged.get("metadata") or {})
    merged["metadata"] = meta
    out["config"] = merged
    return out
