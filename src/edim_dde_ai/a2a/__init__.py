"""Agent-to-agent resolve + dial (ADR-001).

Local subgraphs stay in ``graph.subgraph``. This package owns directory
bindings, resolve policy, and network dialers behind the same YAML
``invoke_agent`` surface.
"""

from __future__ import annotations

from edim_dde_ai.a2a.bindings import (
    AgentBinding,
    clear_runtime_bindings,
    get_binding,
    list_bindings,
    register_runtime_binding,
    resolve_env_label,
)
from edim_dde_ai.a2a.dialers import get_dialer, list_transports, register_dialer
from edim_dde_ai.a2a.resolve import ResolveDecision, resolve_invoke_target

__all__ = [
    "AgentBinding",
    "ResolveDecision",
    "clear_runtime_bindings",
    "get_binding",
    "get_dialer",
    "list_bindings",
    "list_transports",
    "register_dialer",
    "register_runtime_binding",
    "resolve_env_label",
    "resolve_invoke_target",
]
