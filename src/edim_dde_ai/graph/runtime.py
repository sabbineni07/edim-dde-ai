"""Runtime wrapper around a compiled LangGraph agent.

``MetadataAgent`` is the product-facing invoke surface: callers pass and receive
flat dicts. Internally the graph uses an open ``data`` bag so arbitrary metadata
keys survive node merges.

``invoke`` / ``ainvoke`` share Template Method steps ``_prepare`` / ``_extract``.

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
    """

    def __init__(self, definition: AgentDefinition, compiled_graph: Any) -> None:
        self.definition = definition
        self.graph = compiled_graph
        self.agent_id = definition.agent_id

    def _prepare(self, state: dict[str, Any] | None) -> dict[str, Any]:
        return {"data": dict(state or {})}

    def _extract(self, out: dict[str, Any] | None) -> dict[str, Any]:
        return dict((out or {}).get("data") or {})

    def invoke(self, state: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        from edim_dde_ai.observability.langsmith import merge_invoke_kwargs

        kwargs = merge_invoke_kwargs(self.agent_id, kwargs)
        out = self.graph.invoke(self._prepare(state), **kwargs)
        return self._extract(out)

    async def ainvoke(
        self, state: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        from edim_dde_ai.observability.langsmith import merge_invoke_kwargs

        kwargs = merge_invoke_kwargs(self.agent_id, kwargs)
        out = await self.graph.ainvoke(self._prepare(state), **kwargs)
        return self._extract(out)

    def __repr__(self) -> str:
        return f"MetadataAgent(agent_id={self.agent_id!r})"
