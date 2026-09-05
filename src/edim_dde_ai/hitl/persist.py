"""Agent-agnostic HITL post-resume recommendation persist registry.

Business purpose
----------------
Hosts must not branch on product ``agent_id`` to decide *how* to persist after
HITL. Agents (or the API) register adapters; the framework only invokes the
adapter when ``should_persist_after_hitl`` is true.

Adapters live outside this package (domain/API) and return an updated state
dict (typically with ``recommendation_id`` / ``recommendation_status``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from edim_dde_ai.hitl.policy import should_persist_after_hitl

logger = logging.getLogger(__name__)

HitlPersistAdapter = Callable[[dict[str, Any], str], dict[str, Any]]
"""``(state, request_id) -> updated_state``."""

_ADAPTERS: dict[str, HitlPersistAdapter] = {}


def register_hitl_persist_adapter(
    agent_id: str, adapter: HitlPersistAdapter
) -> None:
    """Register or replace the post-HITL persist adapter for ``agent_id``."""
    key = str(agent_id or "").strip()
    if not key:
        raise ValueError("agent_id is required to register a HITL persist adapter")
    _ADAPTERS[key] = adapter


def clear_hitl_persist_adapters() -> None:
    """Remove all registered adapters (tests)."""
    _ADAPTERS.clear()


def list_hitl_persist_adapters() -> list[str]:
    """Return registered agent ids (sorted)."""
    return sorted(_ADAPTERS)


def persist_after_hitl_if_needed(
    agent_id: str,
    state: dict[str, Any] | None,
    *,
    request_id: str,
    best_effort: bool = True,
) -> dict[str, Any]:
    """Run the registered adapter when persist is allowed; else return state.

    Args:
        agent_id: Owning agent (lookup key).
        state: Post-resume agent state.
        request_id: Correlation id passed to the adapter.
        best_effort: When true, log adapter failures and return original state.

    Returns:
        Updated state from the adapter, or the input state unchanged.
    """
    out = dict(state or {})
    if not should_persist_after_hitl(out):
        return out
    adapter = _ADAPTERS.get(str(agent_id or "").strip())
    if adapter is None:
        return out
    try:
        result = adapter(out, request_id)
        return dict(result) if isinstance(result, dict) else out
    except Exception:
        if not best_effort:
            raise
        logger.exception(
            "HITL persist adapter failed agent=%s", agent_id
        )
        return out
