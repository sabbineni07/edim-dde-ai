"""Session mode resolution for initialize / converse / regenerate paths.

Modes (written to state as ``session_mode`` by ``session_prepare``):

* ``initialize`` — first turn; run full pipeline from ``initialize_entry``
* ``converse`` — follow-up Q&A / explanation path
* ``regenerate`` — phrase-triggered new recommendation/diagnosis path

Mode is chosen from checkpoint flag ``session_initialized`` plus optional
``regenerate_phrases`` in the YAML ``session`` block.
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.session.policy import SessionPolicy

SESSION_MODE_INITIALIZE = "initialize"
SESSION_MODE_CONVERSE = "converse"
SESSION_MODE_REGENERATE = "regenerate"


def extract_user_message(state: dict[str, Any]) -> str:
    """Normalize engineer input from ``user_message`` or ``message`` (max 8k)."""
    for key in ("user_message", "message"):
        value = str(state.get(key) or "").strip()
        if value:
            return value[:8000]
    return ""


def is_regenerate_intent(message: str, policy: SessionPolicy) -> bool:
    """True when a follow-up should take the regenerate path (phrase match)."""
    if not message or policy.session is None:
        return False
    lowered = message.lower()
    return any(phrase in lowered for phrase in policy.session.regenerate_phrases)


def resolve_session_mode(
    state: dict[str, Any],
    policy: SessionPolicy,
    *,
    checkpoint_initialized: bool = False,
) -> str:
    """Choose initialize, converse, or regenerate for the current invoke.

    Args:
        state: Flat invoke / checkpoint state.
        policy: Parsed YAML memory + session policy.
        checkpoint_initialized: Extra signal when ``session_initialized`` may
            only exist in the checkpointer (merged into state by LangGraph).
    """
    if not policy.enabled or policy.session is None:
        return SESSION_MODE_INITIALIZE
    initialized = bool(state.get("session_initialized") or checkpoint_initialized)
    message = extract_user_message(state)
    if not initialized:
        return SESSION_MODE_INITIALIZE
    if is_regenerate_intent(message, policy):
        return SESSION_MODE_REGENERATE
    return SESSION_MODE_CONVERSE
