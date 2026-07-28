"""Build LangGraph StateGraph from AgentDefinition (Builder pattern).

``GraphBuilder`` walks an ``AgentDefinition``: resolve node/router factories from
registries, adapt flat-state callables to the internal ``data`` bag, wire edges,
then ``compile()``. Prefer ``build_graph(definition)`` as the public facade.

Router factories are invoked with ``cond.config`` at build time::

    factory = get_router_factory(cond.router)
    router_fn = factory(dict(cond.config))
    adapt_router(router_fn)
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.graph.adapters import adapt_node, adapt_router
from edim_dde_ai.registry.nodes import get_node_factory
from edim_dde_ai.registry.routers import get_router_factory


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Shallow-merge state updates (open metadata bag)."""
    out = dict(left or {})
    out.update(right or {})
    return out


class AgentState(TypedDict):
    """Internal LangGraph state: one open dict channel for metadata agents."""

    data: Annotated[dict[str, Any], _merge_dicts]


def _map_target(target: str):
    return END if target == "END" else target


class GraphBuilder:
    """Incremental builder for a LangGraph graph from an AgentDefinition."""

    def __init__(self, definition: AgentDefinition) -> None:
        self.definition = definition
        self._builder: StateGraph = StateGraph(AgentState)

    def add_nodes(self) -> GraphBuilder:
        for node in self.definition.nodes:
            factory = get_node_factory(node.type)
            cfg = dict(node.config)
            cfg.setdefault("agent_id", self.definition.agent_id)
            runnable = factory(cfg)
            self._builder.add_node(node.id, adapt_node(runnable))
        return self

    def set_entry(self) -> GraphBuilder:
        self._builder.set_entry_point(self.definition.graph_entry)
        return self

    def add_edges(self) -> GraphBuilder:
        for src, tgt in self.definition.edges:
            if src == "START":
                # Entry is set via set_entry_point(graph_entry); START is declarative only.
                continue
            self._builder.add_edge(src, _map_target(tgt))
        return self

    def add_conditional_edges(self) -> GraphBuilder:
        for cond in self.definition.conditional_edges:
            factory = get_router_factory(cond.router)
            router_fn = factory(dict(cond.config))
            mapping = {k: _map_target(v) for k, v in cond.mapping.items()}
            self._builder.add_conditional_edges(
                cond.source, adapt_router(router_fn), mapping
            )
        return self

    def compile(self):
        return self._builder.compile()


def build_graph(definition: AgentDefinition):
    """Compile a LangGraph graph from an agent definition (public facade)."""
    return (
        GraphBuilder(definition)
        .add_nodes()
        .set_entry()
        .add_edges()
        .add_conditional_edges()
        .compile()
    )
