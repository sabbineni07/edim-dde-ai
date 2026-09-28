"""Agent-to-agent resolve, dial, and call envelope (ADR-001 / ADR-002).

Preferred Agent1→Agent2 API is ``call_agent`` (request/response envelope).
YAML ``invoke_agent`` subgraph embed remains for optional same-process pack
reuse — not the recommended A2A path.
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
from edim_dde_ai.a2a.call import call_agent
from edim_dde_ai.a2a.dialers import get_dialer, list_transports, register_dialer
from edim_dde_ai.a2a.envelope import (
    STATUS_COMPLETED,
    STATUS_INPUT_NEEDED,
    STATUS_RUNNING,
    build_call_envelope,
    needs_continue,
    parse_call_envelope,
)
from edim_dde_ai.a2a.resolve import ResolveDecision, resolve_invoke_target
from edim_dde_ai.a2a.tasks import (
    clear_a2a_tasks,
    configure_task_store_from_env,
    get_task,
)
from edim_dde_ai.a2a.turns import clear_conversation_turns

__all__ = [
    "AgentBinding",
    "ResolveDecision",
    "STATUS_COMPLETED",
    "STATUS_INPUT_NEEDED",
    "STATUS_RUNNING",
    "build_call_envelope",
    "call_agent",
    "clear_a2a_tasks",
    "clear_conversation_turns",
    "clear_runtime_bindings",
    "configure_task_store_from_env",
    "get_binding",
    "get_dialer",
    "get_task",
    "list_bindings",
    "list_transports",
    "needs_continue",
    "parse_call_envelope",
    "register_dialer",
    "register_runtime_binding",
    "resolve_env_label",
    "resolve_invoke_target",
]
