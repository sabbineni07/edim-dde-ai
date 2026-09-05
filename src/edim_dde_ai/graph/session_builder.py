"""Session-aware graph compile: flat ``build_graph`` + multi-turn + checkpointer.

Mental model::

    build_session_graph ≈ build_graph + initialize/converse/regenerate + checkpointer

Assembly order (same shape as ``build_graph``)::

    YAML nodes
      → add session_prepare
      → set_entry(session_prepare)   # not YAML graph.entry
      → YAML edges
      → branch session_mode → path entries
      → compile(checkpointer)

``session_prepare`` chooses the mode; follow-ups therefore do not restart at the
YAML pipeline head. When ``memory.strategy`` is ``none``, this falls back to
plain ``build_graph``.

Public API:
  - ``session_enabled(definition)``
  - ``build_session_graph(definition, checkpointer=…)``
  - ``build_graph_for_definition(definition, checkpointer=…)`` — chooser used by
    ``AgentFactory`` / FastAPI
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.graph.builder import GraphBuilder, build_graph
from edim_dde_ai.registry.routers import choice_factory
from edim_dde_ai.session.checkpointer import get_checkpointer
from edim_dde_ai.session.nodes import session_prepare_factory
from edim_dde_ai.session.policy import get_session_policy
from edim_dde_ai.session.router import (
    SESSION_MODE_CONVERSE,
    SESSION_MODE_INITIALIZE,
    SESSION_MODE_REGENERATE,
)

# Preamble node id — must not collide with YAML node ids.
SESSION_PREPARE_NODE = "session_prepare"


def session_enabled(definition: AgentDefinition) -> bool:
    """True when YAML ``memory.strategy`` enables checkpoint-backed sessions."""
    return get_session_policy(definition).enabled


def build_session_graph(
    definition: AgentDefinition,
    *,
    checkpointer: Any | None = None,
):
    """Compile flat graph + session router + LangGraph checkpointer.

    Args:
        definition: Agent with ``memory`` + ``session`` blocks (or memory none).
        checkpointer: Override process default from ``EDIM_CHECKPOINTER``.

    Returns:
        Compiled runnable. Follow-ups must pass the same ``thread_id`` /
        ``conversation_id`` via invoke config (see ``MetadataAgent``).
    """
    policy = get_session_policy(definition)
    if not policy.enabled or policy.session is None:
        return build_graph(definition)

    assert policy.session is not None  # for type checkers
    builder = (
        GraphBuilder(definition)
        .add_nodes()
        .add_node(
            SESSION_PREPARE_NODE,
            session_prepare_factory({"policy": policy}),
        )
        .set_entry_node(SESSION_PREPARE_NODE)
        .add_edges()
        .add_conditional_edges()
        .add_branch(
            SESSION_PREPARE_NODE,
            choice_factory(
                {"field": "session_mode", "default": SESSION_MODE_INITIALIZE}
            ),
            {
                SESSION_MODE_INITIALIZE: policy.initialize_entry,
                SESSION_MODE_CONVERSE: policy.session.converse_entry,
                SESSION_MODE_REGENERATE: policy.session.regenerate_entry,
            },
        )
    )
    saver = checkpointer if checkpointer is not None else get_checkpointer()
    return builder.compile(checkpointer=saver)


def build_graph_for_definition(
    definition: AgentDefinition,
    *,
    checkpointer: Any | None = None,
):
    """Choose session vs plain compile for an agent definition.

    FastAPI / ``AgentFactory`` should call this (not ``build_graph`` alone) so
    multi-turn YAML agents get checkpointer + routing automatically.
    """
    if session_enabled(definition):
        return build_session_graph(definition, checkpointer=checkpointer)
    return build_graph(definition)
