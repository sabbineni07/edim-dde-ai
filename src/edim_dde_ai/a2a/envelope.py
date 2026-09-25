"""A2A call envelope (ADR-002) — request/response between agents.

Statuses:
  * ``completed`` — task finished; ``state`` holds the result
  * ``input_needed`` — peer needs another turn (HITL / clarify); continue
    with the same ``conversation_id``
  * ``running`` — long-running work accepted; poll later with ``task_id``
    (stub-friendly; async worker not required for the contract)
  * ``waiting`` — alias of ``input_needed`` for HITL-shaped peers (compat)
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

CallStatus = Literal["completed", "input_needed", "running", "waiting", "error"]

STATUS_COMPLETED = "completed"
STATUS_INPUT_NEEDED = "input_needed"
STATUS_RUNNING = "running"
STATUS_WAITING = "waiting"  # HITL compat → treat like input_needed
STATUS_ERROR = "error"

_TERMINAL_OK = frozenset({STATUS_COMPLETED})
_NEEDS_CONTINUE = frozenset({STATUS_INPUT_NEEDED, STATUS_WAITING})


def normalize_status(raw: str | None) -> str:
    """Map peer/HITL status strings onto the ADR-002 vocabulary."""
    s = (raw or "").strip().lower()
    if s in ("waiting", "waiting_hitl"):
        return STATUS_INPUT_NEEDED
    if s in (
        STATUS_COMPLETED,
        STATUS_INPUT_NEEDED,
        STATUS_RUNNING,
        STATUS_ERROR,
    ):
        return s
    if not s:
        return STATUS_COMPLETED
    return s


def build_call_envelope(
    *,
    agent_id: str,
    request_id: str,
    state: dict[str, Any] | None,
    status: str | None = None,
    conversation_id: str | None = None,
    task_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build the stable A2A invoke response envelope."""
    final = dict(state or {})
    cid = (
        (conversation_id or "").strip()
        or str(final.get("conversation_id") or "").strip()
        or str(final.get("thread_id") or "").strip()
        or None
    )
    tid = (task_id or "").strip() or str(final.get("task_id") or "").strip() or None
    sid = (session_id or "").strip() or str(final.get("session_id") or "").strip() or None

    # Prefer explicit status; else derive from state hooks / HITL.
    if status:
        st = normalize_status(status)
    elif str(final.get("a2a_status") or "").strip():
        st = normalize_status(str(final.get("a2a_status")))
    elif str(final.get("hitl_status") or "").strip().lower() in (
        "waiting",
        "waiting_hitl",
    ):
        st = STATUS_INPUT_NEEDED
    else:
        st = STATUS_COMPLETED

    if cid:
        final.setdefault("conversation_id", cid)
        final.setdefault("thread_id", cid)
    if tid:
        final.setdefault("task_id", tid)

    return {
        "agent_id": agent_id,
        "request_id": request_id,
        "status": st,
        "conversation_id": cid,
        "task_id": tid,
        "session_id": sid,
        "state": final,
    }


def parse_call_envelope(body: dict[str, Any]) -> dict[str, Any]:
    """Normalize a peer JSON body into a call envelope.

    Accepts either the ADR-002 envelope or a bare state dict (legacy dial).
    """
    if not isinstance(body, dict):
        raise ValueError("call envelope must be an object")
    if "state" in body or "status" in body or "agent_id" in body:
        state = body.get("state") if isinstance(body.get("state"), dict) else dict(body)
        return build_call_envelope(
            agent_id=str(body.get("agent_id") or state.get("agent_id") or ""),
            request_id=str(body.get("request_id") or state.get("request_id") or uuid.uuid4()),
            state=state,
            status=body.get("status"),
            conversation_id=body.get("conversation_id"),
            task_id=body.get("task_id"),
            session_id=body.get("session_id"),
        )
    return build_call_envelope(
        agent_id=str(body.get("agent_id") or ""),
        request_id=str(body.get("request_id") or uuid.uuid4()),
        state=body,
    )


def needs_continue(envelope: dict[str, Any]) -> bool:
    """True when the caller should send another turn on the same conversation."""
    return normalize_status(str(envelope.get("status") or "")) in _NEEDS_CONTINUE


def is_running(envelope: dict[str, Any]) -> bool:
    """True when the peer accepted async work (poll with ``task_id``)."""
    return normalize_status(str(envelope.get("status") or "")) == STATUS_RUNNING
