"""Built-in session nodes prepended to checkpoint-backed agent graphs.

``session_prepare`` is the graph entry for multi-turn agents. It:

1. Appends the current user message to ``messages``
2. Sets ``session_mode`` (initialize | converse | regenerate)
3. Builds ``conversation_context`` (windowed) for LLM prompts

Downstream conditional edges then jump to the YAML path entry for that mode.
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.session.messages import (
    append_message,
    format_messages_for_prompt,
    normalize_messages,
    trim_messages,
)
from edim_dde_ai.session.policy import SessionPolicy
from edim_dde_ai.session.router import extract_user_message, resolve_session_mode


def session_prepare_factory(config: dict[str, Any]):
    """Graph-build factory for the session routing preamble node.

    Config must include ``policy: SessionPolicy`` (injected by ``build_session_graph``).
    """
    policy = config["policy"]
    if not isinstance(policy, SessionPolicy):
        raise TypeError("session.prepare requires SessionPolicy in config.policy")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        message = extract_user_message(state)
        messages = normalize_messages(state.get("messages"))
        if message:
            messages = append_message(messages, role="user", content=message)
        mode = resolve_session_mode(
            state,
            policy,
            checkpoint_initialized=bool(state.get("session_initialized")),
        )
        windowed = trim_messages(
            messages,
            k=policy.memory.k,
            max_chars=policy.memory.context_chars,
        )
        updates: dict[str, Any] = {
            "session_mode": mode,
            "messages": messages,
            "conversation_context": format_messages_for_prompt(windowed),
        }
        if message:
            updates["user_message"] = message
        return updates

    return _node
