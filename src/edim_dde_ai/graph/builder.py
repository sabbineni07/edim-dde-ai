"""Build LangGraph StateGraph from AgentDefinition (Builder pattern).

Business purpose:
  Walk an ``AgentDefinition``: resolve node/router factories from registries,
  wrap nodes with HITL skip-until-resume, wire edges, then ``compile()``.
  All graphs use one flat dict state shape (shallow-merge reducer).

Canonical compile order (plain and session graphs)::

    nodes → set_entry(…) → edges → compile

Public API:
  - ``AgentState`` — reducer-backed flat mapping (canonical graph state)
  - ``FlatAgentState`` — alias of ``AgentState`` (compat)
  - ``GraphBuilder`` — incremental builder used by ``build_graph`` / session
  - ``build_graph(definition)`` — one-shot compile facade (YAML entry)
  - ``build_flat_graph(definition)`` — deprecated alias of ``build_graph``

See also:
  ``graph.session_builder`` — ``build_session_graph`` ≈ build_graph + multi-turn
  modes + checkpointer (entry = ``session_prepare``).
"""

from __future__ import annotations

import warnings
from typing import Annotated, Any, Callable

from langgraph.graph import END, StateGraph

from edim_dde_ai.core.bindings import (
    resolve_llm_binding,
    resolve_search_binding,
    resolve_sql_warehouse_binding,
)
from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.hitl.decorator import NodeFn, skip_until_resume
from edim_dde_ai.hitl.gate import apply_gate_build_config
from edim_dde_ai.registry.nodes import get_node_factory
from edim_dde_ai.registry.routers import get_router_factory


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Shallow-merge state updates (open metadata bag).

    Later node updates overwrite same keys; nested dicts are not deep-merged.
    """
    out = dict(left or {})
    out.update(right or {})
    return out


# Flat dict in/out for every compiled graph (FastAPI, Agent Server, sessions).
AgentState = Annotated[dict[str, Any], _merge_dicts]
FlatAgentState = AgentState  # backward-compatible alias


def _map_target(target: str):
    """Map YAML ``END`` sentinel to LangGraph ``END``; leave node ids as-is."""
    return END if target == "END" else target


class GraphBuilder:
    """Incremental builder for a flat-state LangGraph graph from an AgentDefinition.

    Typical plain-agent flow::

        GraphBuilder(defn).add_nodes().set_entry().add_edges().add_conditional_edges().compile()

    Session graphs use the same steps but call ``set_entry_node("session_prepare")``
    after registering that preamble node (see ``build_session_graph``).
    """

    def __init__(self, definition: AgentDefinition) -> None:
        self.definition = definition
        self._builder: StateGraph = StateGraph(AgentState)

    def add_nodes(self) -> GraphBuilder:
        """Register each YAML node via its factory + ``skip_until_resume``.

        Injects ``agent_id`` into config for prompt/LLM nodes. For
        ``invoke_agent``, preserves YAML target ``agent_id`` and sets
        ``caller_agent_id`` to the parent. For ``hitl.gate``, injects node id
        and ``hitl.enabled``.

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
            if node.type == "hitl.gate":
                apply_gate_build_config(cfg, node, self.definition)
            runnable = skip_until_resume(node.id, factory(cfg))
            self._builder.add_node(node.id, runnable)
        return self

    def add_node(self, node_id: str, runnable: NodeFn) -> GraphBuilder:
        """Register an extra runtime node not declared in YAML (e.g. session_prepare).

        Returns:
            ``self`` for chaining.
        """
        self._builder.add_node(node_id, runnable)
        return self

    def set_entry(self) -> GraphBuilder:
        """Set LangGraph entry to ``definition.graph_entry`` (YAML start node).

        Returns:
            ``self`` for chaining.
        """
        return self.set_entry_node(self.definition.graph_entry)

    def set_entry_node(self, node_id: str) -> GraphBuilder:
        """Set LangGraph entry to an explicit node id (e.g. ``session_prepare``).

        Prefer calling this after the entry node exists and before ``add_edges``,
        matching the plain ``build_graph`` assembly order.

        Returns:
            ``self`` for chaining.
        """
        self._builder.set_entry_point(node_id)
        return self

    def add_edges(self) -> GraphBuilder:
        """Wire unconditional YAML edges; skip declarative ``START``.

        ``START`` is documentation in YAML only — the real entry is set via
        ``set_entry`` / ``set_entry_node``.

        Returns:
            ``self`` for chaining.
        """
        for src, tgt in self.definition.edges:
            if src == "START":
                continue
            self._builder.add_edge(src, _map_target(tgt))
        return self

    def add_conditional_edges(self) -> GraphBuilder:
        """Wire YAML conditional edges via registered router factories.

        Returns:
            ``self`` for chaining.
        """
        for cond in self.definition.conditional_edges:
            factory = get_router_factory(cond.router)
            router_fn = factory(dict(cond.config))
            mapping = {k: _map_target(v) for k, v in cond.mapping.items()}
            self._builder.add_conditional_edges(cond.source, router_fn, mapping)
        return self

    def add_branch(
        self,
        source: str,
        router: Callable[[dict[str, Any]], str],
        mapping: dict[str, str],
    ) -> GraphBuilder:
        """Wire an extra conditional branch (e.g. session mode → path entry).

        Returns:
            ``self`` for chaining.
        """
        resolved = {k: _map_target(v) for k, v in mapping.items()}
        self._builder.add_conditional_edges(source, router, resolved)
        return self

    def compile(self, *, checkpointer: Any | None = None):
        """Compile the underlying ``StateGraph``.

        Args:
            checkpointer: Optional LangGraph checkpointer. Required for durable
                multi-turn sessions (``EDIM_CHECKPOINTER``); omit for single-turn.

        Returns:
            LangGraph compiled runnable.
        """
        if checkpointer is not None:
            return self._builder.compile(checkpointer=checkpointer)
        return self._builder.compile()


def build_graph(definition: AgentDefinition, *, checkpointer: Any | None = None):
    """Compile a flat-state LangGraph graph from an agent definition.

    Assembly: ``nodes → set_entry(yaml) → edges → compile``.

    This is the single-turn / Agent Server path. For FastAPI multi-turn agents
    with ``memory`` + ``session`` YAML, prefer ``build_session_graph`` (or
    ``build_graph_for_definition``, which chooses automatically).

    Args:
        definition: Validated ``AgentDefinition``.
        checkpointer: Optional LangGraph checkpointer (rarely needed here;
            session graphs attach it themselves).

    Returns:
        Compiled LangGraph runnable (flat ``dict`` in/out).
    """
    return (
        GraphBuilder(definition)
        .add_nodes()
        .set_entry()
        .add_edges()
        .add_conditional_edges()
        .compile(checkpointer=checkpointer)
    )


def build_flat_graph(definition: AgentDefinition, *, checkpointer: Any | None = None):
    """Deprecated alias of ``build_graph`` (flat is the only state shape).

    Prefer ``build_graph``. Kept for older import sites.
    """
    warnings.warn(
        "build_flat_graph() is deprecated; use build_graph() (flat state is canonical).",
        DeprecationWarning,
        stacklevel=2,
    )
    return build_graph(definition, checkpointer=checkpointer)
