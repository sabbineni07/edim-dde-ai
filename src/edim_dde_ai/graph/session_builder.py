"""Compile checkpoint-backed session graphs with init/converse/regenerate routing."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.graph.builder import GraphBuilder, build_flat_graph
from edim_dde_ai.registry.routers import choice_factory
from edim_dde_ai.session.checkpointer import get_checkpointer
from edim_dde_ai.session.nodes import session_prepare_factory
from edim_dde_ai.session.policy import SessionPolicy, get_session_policy
from edim_dde_ai.session.router import (
    SESSION_MODE_CONVERSE,
    SESSION_MODE_INITIALIZE,
    SESSION_MODE_REGENERATE,
)

SESSION_PREPARE_NODE = "session_prepare"


def session_enabled(definition: AgentDefinition) -> bool:
    """Return whether the agent should compile with session routing."""
    return get_session_policy(definition).enabled


def build_session_graph(
    definition: AgentDefinition,
    *,
    checkpointer: Any | None = None,
):
    """Compile a flat-state graph with session routing and a LangGraph checkpointer.

    When ``memory.strategy`` is ``none``, this falls back to ``build_flat_graph``.
    """
    policy = get_session_policy(definition)
    if not policy.enabled or policy.session is None:
        from edim_dde_ai.graph.builder import build_flat_graph

        return build_flat_graph(definition)

    inner = (
        GraphBuilder(definition, flat_state=True)
        .add_nodes()
        .add_edges()
        .add_conditional_edges()
    )
    builder: StateGraph = inner._builder  # noqa: SLF001 — shared compile path

    prepare = session_prepare_factory({"policy": policy})
    builder.add_node(SESSION_PREPARE_NODE, prepare)
    builder.set_entry_point(SESSION_PREPARE_NODE)

    route = choice_factory({"field": "session_mode", "default": SESSION_MODE_INITIALIZE})
    builder.add_conditional_edges(
        SESSION_PREPARE_NODE,
        route,
        {
            SESSION_MODE_INITIALIZE: policy.initialize_entry,
            SESSION_MODE_CONVERSE: policy.session.converse_entry,
            SESSION_MODE_REGENERATE: policy.session.regenerate_entry,
        },
    )

    saver = checkpointer if checkpointer is not None else get_checkpointer()
    return builder.compile(checkpointer=saver)


def build_graph_for_definition(
    definition: AgentDefinition,
    *,
    checkpointer: Any | None = None,
):
    """Compile the appropriate graph surface for an agent definition."""
    if session_enabled(definition):
        return build_session_graph(definition, checkpointer=checkpointer)
    return build_flat_graph(definition)
