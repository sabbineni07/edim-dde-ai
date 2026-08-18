"""Decorator: skip graph nodes until a HITL resume point.

Business purpose
----------------
On resume, the same compiled graph is invoked with ``hitl_resume_at`` set to
the gate node id. Wrapping every node avoids re-running SQL/LLM work before
the gate without a LangGraph checkpointer.

Public API
----------
* ``skip_until_resume(node_id, fn)`` — Decorator around a flat-state node
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.graph.adapters import NodeFn

RESUME_AT_KEY = "hitl_resume_at"


def skip_until_resume(node_id: str, fn: NodeFn) -> NodeFn:
    """Return ``{}`` for nodes before ``state[hitl_resume_at]`` (Decorator).

    Args:
        node_id: This graph node id.
        fn: Flat-state node callable.

    Returns:
        Wrapped node. When ``hitl_resume_at`` is unset, ``fn`` always runs.
    """

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        resume_at = state.get(RESUME_AT_KEY)
        if resume_at and resume_at != node_id:
            return {}
        return fn(state)

    return _node
