"""Builtin graph node types for edim-dde-ai.

Business purpose:
  Importing this package loads ``builtin`` and seeds the node registry with
  allowlisted factories (passthrough, llm_chain, rag.retrieve, …). Apps should
  import ``edim_dde_ai.nodes`` (or the top-level package) before building graphs.

Public API:
  - ``builtin`` — module exposing factories and ``BUILTIN_NODE_FACTORIES``
"""

from edim_dde_ai.nodes import builtin as builtin

__all__ = ["builtin"]
