"""``call_agent`` — preferred Agent1→Agent2 request/response API (ADR-002).

Resolves a logical ``agent_id`` via the directory, then dials remote HTTP or
invokes the local ``MetadataAgent`` with the same envelope contract.
"""

from __future__ import annotations

import uuid
from typing import Any

from edim_dde_ai.a2a.correlation import child_correlation
from edim_dde_ai.a2a.dialers import get_dialer
from edim_dde_ai.a2a.envelope import (
    STATUS_RUNNING,
    build_call_envelope,
    parse_call_envelope,
)
from edim_dde_ai.a2a.resolve import resolve_invoke_target
from edim_dde_ai.observability.base import build_run_config


def call_agent(
    agent_id: str,
    input: dict[str, Any] | None = None,
    *,
    conversation_id: str | None = None,
    request_id: str | None = None,
    resolve: str | None = None,
    async_accept: bool = False,
) -> dict[str, Any]:
    """Call a peer agent by logical id; return an ADR-002 call envelope.

    Args:
        agent_id: Logical target (never a URL).
        input: Flat state / message bag for the peer.
        conversation_id: Multi-turn key; minted when omitted and peer continues.
        request_id: Hop correlation id (tracing); minted when omitted.
        resolve: Optional ``auto``|``local``|``remote`` override.
        async_accept: When true, ask the peer to accept work as ``running``
            (peer may still complete synchronously).

    Returns:
        Envelope dict with ``status``, ``state``, ``conversation_id``, …
    """
    target = (agent_id or "").strip()
    if not target:
        raise ValueError("call_agent requires non-empty agent_id")

    payload = dict(input or {})
    rid = (request_id or str(payload.get("request_id") or "")).strip() or str(
        uuid.uuid4()
    )
    cid = (
        (conversation_id or "").strip()
        or str(payload.get("conversation_id") or "").strip()
        or str(payload.get("thread_id") or "").strip()
        or str(uuid.uuid4())
    )
    payload["request_id"] = rid
    payload["conversation_id"] = cid
    payload["thread_id"] = cid
    if async_accept:
        payload["a2a_async"] = True

    decision = resolve_invoke_target(target, resolve=resolve)
    parent_state = {"request_id": rid, "span_id": payload.get("span_id")}
    _config, headers, extras = child_correlation(parent_state, child_agent_id=target)
    payload.update(extras)

    if decision.mode == "remote":
        assert decision.binding is not None
        transport = str(decision.binding.get("transport") or "http")
        dialer = get_dialer(transport)
        invoke_envelope = getattr(dialer, "invoke_envelope", None)
        if callable(invoke_envelope):
            raw = invoke_envelope(
                decision.binding, payload, headers=headers
            )
            env = parse_call_envelope(raw if isinstance(raw, dict) else {})
        else:
            child_state = dialer.invoke(decision.binding, payload, headers=headers)
            env = build_call_envelope(
                agent_id=target,
                request_id=rid,
                state=child_state if isinstance(child_state, dict) else {},
                conversation_id=cid,
            )
        env["conversation_id"] = env.get("conversation_id") or cid
        env["request_id"] = env.get("request_id") or rid
        return env

    from edim_dde_ai.registry.agents import create_agent
    from edim_dde_ai.session.policy import get_session_policy

    config = build_run_config(
        agent_id=target,
        request_id=rid,
        metadata={"edim_a2a": True},
    )
    # Only attach LangGraph thread_id when the peer has conversational memory.
    # ADR-002 conversation_id still rides in flat state for multi-turn bags.
    try:
        from edim_dde_ai.registry.agents import get_agent_definition

        if get_session_policy(get_agent_definition(target)).enabled:
            configurable = dict(config.get("configurable") or {})
            configurable["thread_id"] = cid
            config["configurable"] = configurable
    except Exception:  # noqa: BLE001 — treat as non-session
        pass
    final = create_agent(target).invoke(payload, config=config)
    status = None
    if isinstance(final, dict) and str(final.get("a2a_status") or "").strip():
        status = str(final.get("a2a_status"))
    elif async_accept and isinstance(final, dict) and final.get("task_id"):
        status = STATUS_RUNNING
    return build_call_envelope(
        agent_id=target,
        request_id=rid,
        state=final if isinstance(final, dict) else {},
        status=status,
        conversation_id=cid,
    )
