"""Build LangGraph StateGraph from AgentDefinition (Builder pattern).

Business purpose:
  Walk an ``AgentDefinition``: resolve node/router factories from registries,
  adapt flat-state callables to the internal ``data`` bag, wire edges, then
  ``compile()``. Prefer ``build_graph(definition)`` as the public facade.

Public API:
  - ``AgentState`` — TypedDict with shallow-merged ``data`` channel
  - ``GraphBuilder`` — incremental builder (add_nodes → edges → compile)
  - ``build_graph(definition)`` — one-shot compile facade

Router factories are invoked with ``cond.config`` at build time::

    factory = get_router_factory(cond.router)
    router_fn = factory(dict(cond.config))
    adapt_router(router_fn)
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from edim_dde_ai.core.bindings import (
    resolve_llm_binding,
    resolve_search_binding,
    resolve_sql_warehouse_binding,
)
from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.graph.adapters import adapt_node, adapt_router
from edim_dde_ai.registry.nodes import get_node_factory
from edim_dde_ai.registry.routers import get_router_factory


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Shallow-merge state updates (open metadata bag).

    Later node updates overwrite same keys; nested dicts are not deep-merged.
    """
    out = dict(left or {})
    out.update(right or {})
    return out


class AgentState(TypedDict):
    """Internal LangGraph state: one open dict channel for metadata agents."""

    data: Annotated[dict[str, Any], _merge_dicts]


def _map_target(target: str):
    """Map YAML ``END`` sentinel to LangGraph ``END``; leave node ids as-is."""
    return END if target == "END" else target


class GraphBuilder:
    """Incremental builder for a LangGraph graph from an AgentDefinition.

    Typical flow::

        GraphBuilder(defn).add_nodes().set_entry().add_edges().add_conditional_edges().compile()
    """

    def __init__(self, definition: AgentDefinition) -> None:
        self.definition = definition
        self._builder: StateGraph = StateGraph(AgentState)

    def add_nodes(self) -> GraphBuilder:
        """Register each definition node via its factory + ``adapt_node``.

        Injects ``agent_id`` into config for prompt/LLM nodes. For
        ``invoke_agent``, preserves YAML target ``agent_id`` and sets
        ``caller_agent_id`` to the parent.

        Returns:
            ``self`` for chaining.
        """
        for node in self.definition.nodes:
            factory = get_node_factory(node.type)
            cfg = dict(node.config)
            cfg.setdefault("agent_id", self.definition.agent_id)
            # For invoke_agent, keep target in agent_id and pass caller separately.
            if node.type == "invoke_agent":
                cfg["caller_agent_id"] = self.definition.agent_id
                # YAML uses agent_id for the *target*; do not overwrite with parent id.
                if "agent_id" in node.config:
                    cfg["agent_id"] = node.config["agent_id"]
            # Optional bindings.llm → inject into llm_chain config.
            if node.type == "llm_chain":
                resolved = resolve_llm_binding(self.definition.bindings)
                if resolved.endpoint:
                    cfg.setdefault("endpoint", resolved.endpoint)
                if resolved.deployment:
                    cfg.setdefault("deployment", resolved.deployment)
                if resolved.temperature is not None:
                    cfg.setdefault("temperature", resolved.temperature)
                if resolved.top_p is not None:
                    cfg.setdefault("top_p", resolved.top_p)
                if resolved.top_k is not None:
                    cfg.setdefault("top_k", resolved.top_k)
                if resolved.max_tokens is not None:
                    cfg.setdefault("max_tokens", resolved.max_tokens)
            # Optional bindings.search → inject into rag.retrieve config.
            if node.type == "rag.retrieve":
                resolved_search = resolve_search_binding(self.definition.bindings)
                if resolved_search.endpoint:
                    cfg.setdefault("endpoint", resolved_search.endpoint)
                if resolved_search.index:
                    cfg.setdefault("index", resolved_search.index)
            # Optional bindings.sql-warehouse → inject into domain.sql.query.
            if node.type == "domain.sql.query":
                resolved_sql = resolve_sql_warehouse_binding(
                    self.definition.bindings
                )
                if resolved_sql.host:
                    cfg.setdefault("server_hostname", resolved_sql.host)
                    cfg.setdefault("host", resolved_sql.host)
                if resolved_sql.http_path:
                    cfg.setdefault("http_path", resolved_sql.http_path)
            runnable = factory(cfg)
            self._builder.add_node(node.id, adapt_node(runnable))
        return self

    def set_entry(self) -> GraphBuilder:
        """Set LangGraph entry to ``definition.graph_entry``.

        Returns:
            ``self`` for chaining.
        """
        self._builder.set_entry_point(self.definition.graph_entry)
        return self

    def add_edges(self) -> GraphBuilder:
        """Wire unconditional edges; skip declarative ``START`` (entry handles it).

        Returns:
            ``self`` for chaining.
        """
        for src, tgt in self.definition.edges:
            if src == "START":
                # Entry is set via set_entry_point(graph_entry); START is declarative only.
                continue
            self._builder.add_edge(src, _map_target(tgt))
        return self

    def add_conditional_edges(self) -> GraphBuilder:
        """Wire conditional edges via registered router factories.

        Returns:
            ``self`` for chaining.
        """
        for cond in self.definition.conditional_edges:
            factory = get_router_factory(cond.router)
            router_fn = factory(dict(cond.config))
            mapping = {k: _map_target(v) for k, v in cond.mapping.items()}
            self._builder.add_conditional_edges(
                cond.source, adapt_router(router_fn), mapping
            )
        return self

    def compile(self):
        """Compile the underlying ``StateGraph``.

        Returns:
            LangGraph compiled runnable.
        """
        return self._builder.compile()


def build_graph(definition: AgentDefinition):
    """Compile a LangGraph graph from an agent definition (public facade).

    Args:
        definition: Validated ``AgentDefinition``.

    Returns:
        Compiled LangGraph runnable (pass to ``MetadataAgent``).
    """
    return (
        GraphBuilder(definition)
        .add_nodes()
        .set_entry()
        .add_edges()
        .add_conditional_edges()
        .compile()
    )
