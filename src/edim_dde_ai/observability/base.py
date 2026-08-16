"""Shared run config helpers (backend-agnostic correlation fields).

Business purpose:
  Build LangGraph ``config`` dicts with ``run_name``, tags, and metadata
  (``agent_id``, ``edim_env``, ``request_id``) so all observability backends
  share the same correlation contract.

Public API:
  - ``build_run_config(...)`` — create a fresh config dict
  - ``merge_base_config(...)`` — merge into existing invoke kwargs
"""

from __future__ import annotations

import os
import uuid
from typing import Any


def build_run_config(
    *,
    agent_id: str,
    request_id: str | None = None,
    extra_tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a LangGraph ``config`` dict with runnable tags/metadata.

    Safe to pass even when a backend is disabled — unused keys are ignored.

    Args:
        agent_id: Agent id (also used as ``run_name``).
        request_id: Correlation id; generated UUID if omitted.
        extra_tags: Additional tag strings.
        metadata: Extra metadata keys merged into the base set.

    Returns:
        Dict with ``run_name``, ``tags``, and ``metadata``.
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


def merge_base_config(
    agent_id: str,
    kwargs: dict[str, Any],
    *,
    request_id: str | None = None,
    extra_tags: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge correlation config into invoke kwargs (shared by all providers).

    Preserves caller ``config`` fields; unions tags; merges metadata with
    caller values winning on key conflicts. If ``config`` is present but not a
    dict, kwargs are returned unchanged.

    Args:
        agent_id: Agent being invoked.
        kwargs: Original ``invoke`` kwargs.
        request_id: Optional override; else reuse existing metadata request_id.
        extra_tags: Backend-specific tags to append.
        extra_metadata: Backend-specific metadata defaults.

    Returns:
        Shallow copy of kwargs with merged ``config``.
    """
    out = dict(kwargs)
    existing = out.get("config")
    if existing is None:
        existing = {}
    elif not isinstance(existing, dict):
        return out

    built = build_run_config(
        agent_id=agent_id,
        request_id=request_id or (existing.get("metadata") or {}).get("request_id"),
        extra_tags=extra_tags,
        metadata=extra_metadata,
    )
    merged = dict(existing)
    if "run_name" not in merged:
        merged["run_name"] = built["run_name"]
    tags = list(merged.get("tags") or [])
    for t in built["tags"]:
        if t not in tags:
            tags.append(t)
    merged["tags"] = tags
    # Built defaults first; existing caller metadata wins on conflicts.
    meta = dict(built["metadata"])
    meta.update(merged.get("metadata") or {})
    merged["metadata"] = meta
    out["config"] = merged
    return out
