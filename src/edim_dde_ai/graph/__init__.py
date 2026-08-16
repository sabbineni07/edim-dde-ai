"""LangGraph construction and runtime facade.

Business purpose:
  Compile an ``AgentDefinition`` into a runnable graph and expose a flat-dict
  ``MetadataAgent`` invoke surface for products and CLI.

Public API:
  - ``AgentState`` — internal TypedDict (``data`` bag)
  - ``build_graph(definition)`` — compile LangGraph from definition
  - ``MetadataAgent`` — ``invoke`` / ``ainvoke`` facade
"""

from edim_dde_ai.graph.builder import AgentState, build_graph
from edim_dde_ai.graph.runtime import MetadataAgent

__all__ = [
    "AgentState",
    "build_graph",
    "MetadataAgent",
]
