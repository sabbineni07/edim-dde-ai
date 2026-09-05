"""LangGraph construction and runtime facade.

* ``build_graph`` — plain flat compile (YAML entry)
* ``build_session_graph`` / ``build_graph_for_definition`` — multi-turn + checkpointer
* ``MetadataAgent`` — product invoke/ainvoke wrapper

Flat ``AgentState`` is the only graph state shape.
"""

from edim_dde_ai.graph.builder import (
    AgentState,
    FlatAgentState,
    build_flat_graph,
    build_graph,
)
from edim_dde_ai.graph.session_builder import (
    build_graph_for_definition,
    build_session_graph,
    session_enabled,
)
from edim_dde_ai.graph.runtime import MetadataAgent

__all__ = [
    "AgentState",
    "FlatAgentState",
    "MetadataAgent",
    "build_graph",
    "build_flat_graph",
    "build_graph_for_definition",
    "build_session_graph",
    "session_enabled",
]
