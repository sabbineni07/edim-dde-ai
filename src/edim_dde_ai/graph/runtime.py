"""Runtime wrapper around a compiled LangGraph agent.

Business purpose:
  Product-facing invoke surface: callers pass and receive flat dicts. Session
  agents compile with LangGraph checkpoints and route initialize / converse /
  regenerate paths; single-turn agents use a flat graph without checkpoints.

Public API:
  - ``MetadataAgent`` — ``invoke`` / ``ainvoke`` over a compiled graph

Example::

    agent.invoke({"cluster_id": "c1", "include_explanation": True})
    agent.invoke(
        {"thread_id": tid, "message": "why?"},
        config={"configurable": {"thread_id": tid}},
    )
"""

from __future__ import annotations

import uuid
from typing import Any

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import ConversationMemoryDisabledError, HitlPaused
from edim_dde_ai.session.messages import append_message, assistant_text_from_final, normalize_messages
from edim_dde_ai.session.policy import SessionPolicy, get_session_policy
from edim_dde_ai.session.router import SESSION_MODE_INITIALIZE


class MetadataAgent:
    """Thin invoke/ainvoke facade over a compiled flat-state graph.

    For session-enabled agents this wrapper also:

    * Ensures ``config.configurable.thread_id`` (alias ``conversation_id``)
    * Rejects follow-up ids when memory is disabled
    * Writes assistant turn + ``session_initialized`` back into the checkpointer
    """

    def __init__(
        self,
        definition: AgentDefinition,
        compiled_graph: Any,
        *,
        policy: SessionPolicy | None = None,
    ) -> None:
        self.definition = definition
        self.graph = compiled_graph
        self.agent_id = definition.agent_id
        self.policy = policy or get_session_policy(definition)

    def _merge_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Attach observability tags/metadata to LangGraph invoke kwargs."""
        from edim_dde_ai.observability import get_observability_provider

        return get_observability_provider().merge_invoke_kwargs(self.agent_id, kwargs)

    @staticmethod
    def _thread_id(state: dict[str, Any], kwargs: dict[str, Any]) -> str:
        """Resolve thread id from config or flat state (``thread_id`` / ``conversation_id``)."""
        config = kwargs.get("config") or {}
        configurable = config.get("configurable") or {}
        for key in ("thread_id", "conversation_id"):
            value = str(configurable.get(key) or state.get(key) or "").strip()
            if value:
                return value
        return ""

    def _validate_follow_up(self, state: dict[str, Any], kwargs: dict[str, Any]) -> None:
        """Reject conversation ids when the agent has ``memory.strategy: none``."""
        if self.policy.enabled:
            return
        thread_id = self._thread_id(state, kwargs)
        if thread_id:
            raise ConversationMemoryDisabledError(
                "Conversational memory is disabled for this agent; "
                "configure memory.strategy or remove thread_id/conversation_id"
            )

    def _ensure_thread_config(
        self, state: dict[str, Any], kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Ensure session invokes carry a stable LangGraph ``thread_id``."""
        merged = dict(kwargs)
        if not self.policy.enabled:
            return merged
        config = dict(merged.get("config") or {})
        configurable = dict(config.get("configurable") or {})
        thread_id = self._thread_id(state, merged) or str(uuid.uuid4())
        configurable.setdefault("thread_id", thread_id)
        config["configurable"] = configurable
        merged["config"] = config
        return merged

    def _record_assistant_turn(
        self,
        *,
        config: dict[str, Any],
        final: dict[str, Any],
        mode: str,
    ) -> None:
        """Persist assistant message (and init flag) into the checkpointer."""
        if not self.policy.enabled:
            return
        content = assistant_text_from_final(final)
        if not content:
            return
        current = normalize_messages(final.get("messages"))
        updates: dict[str, Any] = {
            "messages": append_message(current, role="assistant", content=content),
        }
        if mode == SESSION_MODE_INITIALIZE:
            updates["session_initialized"] = True
        try:
            self.graph.update_state(config, updates)
        except Exception:  # noqa: BLE001 — checkpoint write is best-effort
            return
        final.update(updates)

    def invoke(self, state: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Run the compiled graph synchronously; return a flat result dict."""
        payload = dict(state or {})
        self._validate_follow_up(payload, kwargs)
        kwargs = self._ensure_thread_config(payload, self._merge_kwargs(kwargs))
        config = kwargs.get("config") or {}
        try:
            out = self.graph.invoke(payload, **kwargs)
        except HitlPaused as paused:
            return dict(paused.state)
        final = dict(out or {})
        mode = str(final.get("session_mode") or SESSION_MODE_INITIALIZE)
        self._record_assistant_turn(config=config, final=final, mode=mode)
        thread_id = self._thread_id(payload, kwargs)
        if thread_id:
            final.setdefault("thread_id", thread_id)
            final.setdefault("conversation_id", thread_id)
        return final

    async def ainvoke(
        self, state: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Async variant of ``invoke``."""
        payload = dict(state or {})
        self._validate_follow_up(payload, kwargs)
        kwargs = self._ensure_thread_config(payload, self._merge_kwargs(kwargs))
        config = kwargs.get("config") or {}
        try:
            out = await self.graph.ainvoke(payload, **kwargs)
        except HitlPaused as paused:
            return dict(paused.state)
        final = dict(out or {})
        mode = str(final.get("session_mode") or SESSION_MODE_INITIALIZE)
        self._record_assistant_turn(config=config, final=final, mode=mode)
        thread_id = self._thread_id(payload, kwargs)
        if thread_id:
            final.setdefault("thread_id", thread_id)
            final.setdefault("conversation_id", thread_id)
        return final

    def __repr__(self) -> str:
        return f"MetadataAgent(agent_id={self.agent_id!r})"
