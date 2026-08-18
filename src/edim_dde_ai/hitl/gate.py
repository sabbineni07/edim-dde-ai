"""Factory for the ``hitl.gate`` node type.

Business purpose
----------------
Allowlisted YAML type ``hitl.gate``: no-op, pass-through on resume, or persist
a waiting session and raise ``HitlPaused`` (control flow, not a failure).

Public API
----------
* ``hitl_gate_factory`` — ``(config) -> (state) -> updates``
* ``apply_gate_build_config`` — GraphBuilder injects node id + ``hitl.enabled``
"""

from __future__ import annotations

import uuid
from typing import Any

from edim_dde_ai.core.definition import AgentDefinition, NodeSpec
from edim_dde_ai.errors import HitlPaused
from edim_dde_ai.hitl.decorator import RESUME_AT_KEY
from edim_dde_ai.hitl.sessions import (
    STATUS_RESUMED,
    STATUS_WAITING,
    persist_hitl_pause,
    prior_decision_for_gate,
)


def apply_gate_build_config(
    cfg: dict[str, Any],
    node: NodeSpec,
    definition: AgentDefinition,
) -> dict[str, Any]:
    """Inject compile-time HITL fields into the node factory config.

    Args:
        cfg: Mutable factory config (already a copy).
        node: YAML node spec.
        definition: Parent agent definition (reads ``hitl.enabled``).

    Returns:
        The same ``cfg`` mapping (for chaining).
    """
    cfg["node_id"] = node.id
    cfg.setdefault("gate_id", node.id)
    hitl_block = (definition.raw or {}).get("hitl") or {}
    if "enabled" in hitl_block:
        cfg["agent_hitl_enabled"] = bool(hitl_block.get("enabled"))
    return cfg


def hitl_gate_factory(config: dict[str, Any]):
    """Pause the graph until a human decision is recorded on the session.

    When ``hitl.enabled`` is false on the agent (injected as
    ``agent_hitl_enabled``) or state ``skip_hitl`` is true, the node is a no-op.

    If ``state.hitl_decisions[gate_id]`` already has a decision (resume), the
    gate clears ``hitl_resume_at`` and continues.

    Otherwise the node persists a ``waiting_hitl`` session and raises
    ``HitlPaused`` so later nodes do not run.

    Config:
      gate_id / node_id: str — decision key (GraphBuilder injects node id)
      prompt: str — shown to the reviewer (stored on the session)
      agent_id: str — injected by GraphBuilder
      agent_hitl_enabled: bool — from YAML ``hitl.enabled`` (default True if
        the node is present and the block is omitted)

    Example YAML::

        hitl:
          enabled: true
        graph:
          nodes:
            - id: approve
              type: hitl.gate
              prompt: Approve this recommendation?
    """
    gate_id = str(config.get("gate_id") or config.get("node_id") or "approve")
    prompt = str(config.get("prompt") or "Human approval required")
    agent_id = str(config.get("agent_id") or "")
    agent_enabled = bool(config.get("agent_hitl_enabled", True))

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("skip_hitl"):
            return {}
        if not agent_enabled and not state.get("hitl_enabled"):
            return {}

        prior = prior_decision_for_gate(state, gate_id)
        if prior is not None:
            return {
                "hitl_status": STATUS_RESUMED,
                RESUME_AT_KEY: None,
                "hitl_gate_id": gate_id,
                "hitl_decision": prior.get("decision"),
                "hitl_comment": prior.get("comment") or "",
            }

        session_id = str(state.get("session_id") or "").strip() or str(uuid.uuid4())
        request_id = str(state.get("request_id") or "").strip() or None
        snapshot = dict(state)
        snapshot.update(
            {
                "session_id": session_id,
                "hitl_status": STATUS_WAITING,
                "hitl_gate_id": gate_id,
                "hitl_prompt": prompt,
                RESUME_AT_KEY: gate_id,
            }
        )
        persist_hitl_pause(
            session_id=session_id,
            agent_id=agent_id,
            state=snapshot,
            request_id=request_id,
            gate_id=gate_id,
            prompt=prompt,
        )
        raise HitlPaused(session_id=session_id, agent_id=agent_id, state=snapshot)

    return _node
