"""Runtime wrapper around a compiled LangGraph agent.

Business purpose:
  Product-facing invoke surface: callers pass and receive flat dicts. Internally
  the graph uses an open ``data`` bag so arbitrary metadata keys survive node
  merges. Observability providers enrich kwargs before each invoke.

Public API:
  - ``MetadataAgent`` — ``invoke`` / ``ainvoke`` over a compiled graph

Example::

    agent.invoke({"cluster_id": "c1", "include_explanation": True})
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.core.definition import AgentDefinition


class MetadataAgent:
    """Thin invoke/ainvoke facade over a compiled graph.

    Public API uses a flat dict state; internally the graph stores an open
    ``data`` bag so arbitrary metadata keys are preserved across nodes.

    ``invoke`` / ``ainvoke`` share Template Method steps ``_prepare`` / ``_extract``.

    Attributes:
        definition: Source ``AgentDefinition``.
        graph: Compiled LangGraph runnable.
        agent_id: Convenience mirror of ``definition.agent_id``.
    """

    def __init__(self, definition: AgentDefinition, compiled_graph: Any) -> None:
        self.definition = definition
        self.graph = compiled_graph
        self.agent_id = definition.agent_id
        from edim_dde_ai.memory import ConversationMemoryManager, get_memory_policy

        self.memory = ConversationMemoryManager(
            get_memory_policy(definition), agent_id=self.agent_id
        )

    def _prepare(self, state: dict[str, Any] | None) -> dict[str, Any]:
        """Wrap flat caller state into LangGraph ``AgentState``."""
        return {"data": self.memory.prepare(dict(state or {}))}

    def _extract(self, out: dict[str, Any] | None) -> dict[str, Any]:
        """Unwrap the ``data`` bag from graph output."""
        return dict((out or {}).get("data") or {})

    def _merge_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Attach observability tags without copying them into agent state."""
        from edim_dde_ai.observability import get_observability_provider

        return get_observability_provider().merge_invoke_kwargs(self.agent_id, kwargs)

    def _from_paused(self, paused: Any) -> dict[str, Any]:
        """Return the gate snapshot; ``HitlPaused`` is control flow, not a failure."""
        return dict(paused.state)

    def invoke(self, state: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Synchronously run the graph.

        Args:
            state: Flat metadata input (default empty).
            **kwargs: Forwarded to LangGraph after observability merge
                (e.g. ``config=...``).

        Returns:
            Flat metadata dict from the final ``data`` bag.
        """
        from edim_dde_ai.errors import HitlPaused

        kwargs = self._merge_kwargs(kwargs)
        prepared = self.memory.prepare(dict(state or {}))
        try:
            out = self.graph.invoke({"data": prepared}, **kwargs)
        except HitlPaused as paused:
            final = self._from_paused(paused)
        else:
            final = self._extract(out)
        self.memory.record_response(prepared, final)
        return final

    async def ainvoke(
        self, state: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Async variant of ``invoke``.

        Args:
            state: Flat metadata input (default empty).
            **kwargs: Forwarded to LangGraph after observability merge.

        Returns:
            Flat metadata dict from the final ``data`` bag.
        """
        from edim_dde_ai.errors import HitlPaused

        kwargs = self._merge_kwargs(kwargs)
        prepared = self.memory.prepare(dict(state or {}))
        try:
            out = await self.graph.ainvoke({"data": prepared}, **kwargs)
        except HitlPaused as paused:
            final = self._from_paused(paused)
        else:
            final = self._extract(out)
        self.memory.record_response(prepared, final)
        return final

    def __repr__(self) -> str:
        return f"MetadataAgent(agent_id={self.agent_id!r})"
