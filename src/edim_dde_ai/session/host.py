"""Host-agnostic conversation and session projection helpers.

Business purpose
----------------
FastAPI (and other hosts) share the same rules for memory-aware request
normalization and HITL session field projection. These helpers are agent-id
agnostic: they take policies/definitions as inputs, never product DTOs.

Public API
----------
* ``memory_enabled_for_agent`` / ``normalize_conversation_payload``
* ``attach_thread_id``
* ``normalize_http_session_status`` / ``project_session_state`` /
  ``project_session_record``
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from edim_dde_ai.errors import ConversationMemoryDisabledError
from edim_dde_ai.session.policy import get_memory_policy
from edim_dde_ai.store.models import SessionRecord


def memory_enabled_for_agent(agent_id: str) -> bool:
    """Return whether the registered agent accepts conversational follow-ups."""
    # Lazy import: session package loads during graph bootstrap before registry is ready.
    from edim_dde_ai.registry.agents import get_agent_definition

    return get_memory_policy(get_agent_definition(agent_id)).enabled


def normalize_conversation_payload(
    body: Any,
    *,
    request_id: str,
    memory_enabled: bool,
) -> tuple[dict[str, Any], str | None]:
    """Normalize host request body for invoke under the agent memory policy.

    Accepts a mapping or an object with ``model_dump()`` (e.g. Pydantic). Maps
    ``message`` → ``user_message``, stamps ``request_id``, and mints
    ``conversation_id`` / ``thread_id`` when memory is enabled.

    Returns:
        ``(payload, conversation_id)`` where ``conversation_id`` is ``None``
        when memory is disabled.

    Raises:
        ConversationMemoryDisabledError: ``conversation_id`` sent but memory off.
    """
    if hasattr(body, "model_dump") and callable(body.model_dump):
        payload = dict(body.model_dump())
    elif isinstance(body, Mapping):
        payload = dict(body)
    else:
        raise TypeError(
            "normalize_conversation_payload expects a mapping or model_dump()"
        )

    conversation_id = str(payload.get("conversation_id") or "").strip()
    message = payload.pop("message", None)
    payload["request_id"] = request_id
    if message:
        payload["user_message"] = message
    if not memory_enabled:
        if conversation_id:
            raise ConversationMemoryDisabledError(
                "Conversational memory is disabled for this agent; "
                "configure memory.strategy or remove conversation_id"
            )
        payload.pop("conversation_id", None)
        return payload, None
    conversation_id = conversation_id or str(uuid.uuid4())
    payload["conversation_id"] = conversation_id
    payload["thread_id"] = conversation_id
    return payload, conversation_id


def attach_thread_id(
    config: dict[str, Any] | None, conversation_id: str | None
) -> dict[str, Any]:
    """Attach LangGraph ``configurable.thread_id`` when a conversation key is set."""
    if not conversation_id:
        return dict(config or {})
    merged = dict(config or {})
    configurable = dict(merged.get("configurable") or {})
    configurable.setdefault("thread_id", conversation_id)
    merged["configurable"] = configurable
    return merged


def normalize_http_session_status(status: str) -> str:
    """Map in-graph HITL status onto the HTTP session contract."""
    if status in {"resumed", "closed"}:
        return "closed"
    return status


def project_session_state(
    *,
    agent_id: str,
    state: dict[str, Any],
    request_id: str | None = None,
    status_override: str | None = None,
) -> dict[str, Any]:
    """Project flat agent / session state into host session response fields."""
    status = status_override or str(state.get("hitl_status") or "completed")
    status = normalize_http_session_status(status)
    return {
        "session_id": state.get("session_id"),
        "agent_id": agent_id,
        "status": status,
        "hitl_prompt": state.get("hitl_prompt"),
        "hitl_gate_id": state.get("hitl_gate_id"),
        "hitl_decision": state.get("hitl_decision"),
        "request_id": request_id or state.get("request_id"),
        "state": state,
    }


def project_session_record(rec: SessionRecord) -> dict[str, Any]:
    """Project a persisted ``SessionRecord`` into host session response fields."""
    state = dict(rec.state or {})
    extra = rec.extra or {}
    return {
        "session_id": rec.session_id,
        "agent_id": rec.agent_id,
        "status": rec.status,
        "hitl_prompt": extra.get("prompt") or state.get("hitl_prompt"),
        "hitl_gate_id": extra.get("gate_id") or state.get("hitl_gate_id"),
        "hitl_decision": state.get("hitl_decision"),
        "request_id": rec.request_id,
        "state": state,
    }
