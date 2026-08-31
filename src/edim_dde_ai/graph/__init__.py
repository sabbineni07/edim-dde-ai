"""LangGraph construction and runtime facade.

Business purpose:
  Compile an ``AgentDefinition`` into a runnable graph and expose a flat-dict
  ``MetadataAgent`` invoke surface for products and CLI.

Public API:
  - ``AgentState`` — internal TypedDict (``data`` bag)
  - ``FlatAgentState`` — reducer-backed flat mapping for host adapters
  - ``build_graph(definition)`` — compile LangGraph from definition
  - ``build_flat_graph(definition)`` — compile LangGraph with flat public state
  - ``MetadataAgent`` — ``invoke`` / ``ainvoke`` facade
"""

from edim_dde_ai.graph.builder import (
    AgentState,
    FlatAgentState,
    build_flat_graph,
    build_graph,
)
from edim_dde_ai.graph.runtime import MetadataAgent

__all__ = [
    "AgentState",
    "FlatAgentState",
    "build_graph",
    "build_flat_graph",
    "MetadataAgent",
]
