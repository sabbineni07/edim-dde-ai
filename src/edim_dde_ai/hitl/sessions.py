"""HITL session persist / resume against the process StateStore.

Business purpose
----------------
When ``hitl.gate`` pauses a graph, the flat state snapshot is stored as a
``SessionRecord`` (``waiting_hitl``). A human decision is merged and the same
agent is invoked again; nodes before the gate are skipped via ``hitl_resume_at``.

Public API
----------
* ``HITL_DECISIONS`` / ``STATUS_WAITING`` / ``STATUS_CLOSED``
* ``prior_decision_for_gate`` / ``merge_hitl_decision``
* ``persist_hitl_pause`` / ``close_hitl_session`` / ``resume_hitl_session``
"""

from __future__ import annotations

import uuid
from typing import Any

from edim_dde_ai.errors import HitlError
from edim_dde_ai.hitl.decorator import RESUME_AT_KEY
from edim_dde_ai.store.models import AuditEvent, SessionRecord
from edim_dde_ai.store.registry import get_state_store

HITL_DECISIONS = frozenset({"approved", "rejected", "modified"})
STATUS_WAITING = "waiting_hitl"
STATUS_CLOSED = "closed"
STATUS_RESUMING = "resuming"
STATUS_RESUMED = "resumed"


def prior_decision_for_gate(
    state: dict[str, Any], gate_id: str
) -> dict[str, Any] | None:
    """Return the stored decision mapping for ``gate_id``, if present.

    Args:
        state: Flat agent state.
        gate_id: Gate / node id.

    Returns:
        Decision dict with at least ``decision``, or ``None``.
    """
    decisions = state.get("hitl_decisions") or {}
    if not isinstance(decisions, dict):
        return None
    prior = decisions.get(gate_id)
    if isinstance(prior, dict) and prior.get("decision"):
        return prior
    return None


def merge_hitl_decision(
    state: dict[str, Any],
    *,
    session_id: str,
    gate_id: str,
    decision: str,
    comment: str | None = None,
    patch: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    """Return a new state dict with the human decision applied (resume input).

    Args:
        state: Snapshot loaded from the session.
        session_id: Session key.
        gate_id: Gate that paused.
        decision: Allowlisted decision string (already normalized).
        comment: Optional reviewer comment.
        patch: Optional extra keys (typical for ``modified``).
        actor: Optional reviewer identity stored on the decision record.

    Returns:
        Shallow copy of ``state`` with HITL fields set.
    """
    out = dict(state)
    decisions = dict(out.get("hitl_decisions") or {})
    decisions[gate_id] = {
        "decision": decision,
        "comment": comment or "",
        "patch": dict(patch or {}),
        "actor": actor,
    }
    out["hitl_decisions"] = decisions
    out["hitl_decision"] = decision
    out["hitl_comment"] = comment or ""
    out["hitl_status"] = STATUS_RESUMING
    out[RESUME_AT_KEY] = gate_id
    out["session_id"] = session_id
    if patch:
        out.update(patch)
    return out


def _append_audit(
    *,
    action: str,
    agent_id: str | None,
    actor: str,
    detail: dict[str, Any],
) -> None:
    """Append one HITL audit row (shared by pause / resume / close)."""
    get_state_store().append_audit(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            action=action,
            agent_id=agent_id,
            actor=actor,
            detail=detail,
        )
    )


def persist_hitl_pause(
    *,
    session_id: str,
    agent_id: str,
    state: dict[str, Any],
    request_id: str | None = None,
    gate_id: str | None = None,
    prompt: str | None = None,
) -> SessionRecord:
    """Upsert a ``waiting_hitl`` session and append a ``hitl.pause`` audit row.

    Args:
        session_id: Stable session key.
        agent_id: Owning agent id.
        state: Flat snapshot at the gate.
        request_id: Optional correlation id.
        gate_id: YAML node / gate id.
        prompt: Human-facing prompt stored in ``extra``.

    Returns:
        The persisted ``SessionRecord``.
    """
    extra: dict[str, Any] = {}
    if gate_id:
        extra["gate_id"] = gate_id
    if prompt:
        extra["prompt"] = prompt
    record = SessionRecord(
        session_id=session_id,
        agent_id=agent_id,
        status=STATUS_WAITING,
        state=dict(state),
        request_id=request_id,
        extra=extra,
    )
    store = get_state_store()
    store.upsert_session(record)
    _append_audit(
        action="hitl.pause",
        agent_id=agent_id,
        actor="runtime",
        detail={"session_id": session_id, "gate_id": gate_id},
    )
    return record


def close_hitl_session(
    session_id: str,
    state: dict[str, Any],
    *,
    request_id: str | None = None,
) -> SessionRecord | None:
    """Mark a session ``closed`` after a completed (non-paused) resume.

    Args:
        session_id: Session key.
        state: Final flat agent state.
        request_id: Optional correlation id to stamp.

    Returns:
        Updated record, or ``None`` if the session was missing.
    """
    store = get_state_store()
    existing = store.get_session(session_id)
    if existing is None:
        return None
    existing.status = STATUS_CLOSED
    existing.state = dict(state)
    if request_id:
        existing.request_id = request_id
    store.upsert_session(existing)
    _append_audit(
        action="hitl.close",
        agent_id=existing.agent_id,
        actor="runtime",
        detail={"session_id": session_id},
    )
    return existing


def resume_hitl_session(
    session_id: str,
    *,
    decision: str,
    comment: str | None = None,
    patch: dict[str, Any] | None = None,
    actor: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Apply a human decision and continue the paused agent (Facade).

    Args:
        session_id: Existing ``waiting_hitl`` session.
        decision: ``approved`` | ``rejected`` | ``modified``.
        comment: Optional reviewer comment.
        patch: Optional state keys to merge (typical for ``modified``).
        actor: Optional reviewer identity for audit.
        request_id: Correlation id for the resume invoke (defaults to session).

    Returns:
        Flat agent state after resume (may be ``waiting_hitl`` again if another
        gate fires).

    Raises:
        HitlError: Unknown session, wrong status, or invalid decision.
    """
    choice = (decision or "").strip().lower()
    if choice not in HITL_DECISIONS:
        raise HitlError(
            f"hitl decision must be one of {sorted(HITL_DECISIONS)} (got {decision!r})"
        )

    store = get_state_store()
    record = store.get_session(session_id)
    if record is None:
        raise HitlError(f"HITL session not found: {session_id!r}")
    if record.status != STATUS_WAITING:
        raise HitlError(
            f"HITL session {session_id!r} is {record.status!r}, expected {STATUS_WAITING}"
        )

    gate_id = (
        str(record.extra.get("gate_id") or "")
        or str((record.state or {}).get("hitl_gate_id") or "")
        or "approve"
    )
    state = merge_hitl_decision(
        dict(record.state or {}),
        session_id=session_id,
        gate_id=gate_id,
        decision=choice,
        comment=comment,
        patch=patch,
        actor=actor,
    )

    rid = (request_id or record.request_id or "").strip() or str(uuid.uuid4())
    _append_audit(
        action="hitl.resume",
        agent_id=record.agent_id,
        actor=actor or "human",
        detail={"session_id": session_id, "decision": choice, "gate_id": gate_id},
    )

    from edim_dde_ai.observability import build_run_config
    from edim_dde_ai.registry.agents import create_agent

    agent = create_agent(record.agent_id)
    config = build_run_config(agent_id=record.agent_id, request_id=rid)
    out = agent.invoke(state, config=config)

    if out.get("hitl_status") != STATUS_WAITING:
        close_hitl_session(session_id, out, request_id=rid)
        out.setdefault("hitl_status", STATUS_CLOSED)
    return out
