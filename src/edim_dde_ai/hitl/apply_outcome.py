"""Builtin ``hitl.apply_outcome`` — generic post-gate approve / reject / modify.

Business purpose
----------------
After ``hitl.gate`` resumes, set ``hitl_outcome`` / ``status`` / optional
``hitl_next`` without product-specific DTO reshaping. Agents that need extra
work (e.g. rebuild a comparison view) can keep a domain node instead.

Config
------
* ``explain_field`` — state key; when truthy and not rejected → ``hitl_next=explain``
* ``rejected_next`` / ``approved_next`` — override ``hitl_next`` labels (default
  ``end`` / ``explain``-or-``end``)
"""

from __future__ import annotations

from typing import Any


def hitl_apply_outcome_factory(config: dict[str, Any]):
    """Mark HITL outcome on state after the gate continues.

    Args:
        config: Optional ``explain_field`` (default ``include_explanation``).

    Returns:
        Node ``(state) -> partial`` with ``hitl_outcome``, ``status``, ``hitl_next``.
    """
    explain_field = str(config.get("explain_field") or "include_explanation")
    rejected_next = str(config.get("rejected_next") or "end")
    approved_next = config.get("approved_next")  # None → derive from explain_field

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        decision = str(state.get("hitl_decision") or "").strip().lower() or "approved"
        if decision == "rejected":
            return {
                "hitl_outcome": "rejected",
                "status": "rejected",
                "hitl_next": rejected_next,
            }
        want_explain = bool(state.get(explain_field))
        if approved_next is not None:
            nxt = str(approved_next)
        else:
            nxt = "explain" if want_explain else "end"
        return {
            "hitl_outcome": decision,
            "status": "completed",
            "hitl_next": nxt,
        }

    return _node
