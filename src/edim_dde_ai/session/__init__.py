"""LangGraph checkpoint-backed multi-turn session support.

Package layout:

* ``policy`` / ``models`` — YAML ``memory`` + ``session`` parsing
* ``router`` — initialize | converse | regenerate
* ``nodes`` — ``session_prepare`` preamble
* ``messages`` — in-graph message window helpers
* ``checkpointer`` — ``EDIM_CHECKPOINTER`` registry (memory | postgres)
* ``host`` — conversation / session projection helpers (import from
  ``edim_dde_ai.session.host`` to avoid registry circular imports)

Graph wiring lives in ``edim_dde_ai.graph.session_builder``.
"""

from edim_dde_ai.session.checkpointer import (
    clear_checkpointer,
    configure_checkpointer_from_env,
    create_checkpointer,
    get_checkpointer,
    resolve_checkpointer_name,
    set_checkpointer,
)
from edim_dde_ai.session.models import MemoryPolicy
from edim_dde_ai.session.policy import (
    SessionConfig,
    SessionPolicy,
    get_memory_policy,
    get_session_policy,
)
from edim_dde_ai.session.router import (
    SESSION_MODE_CONVERSE,
    SESSION_MODE_INITIALIZE,
    SESSION_MODE_REGENERATE,
    extract_user_message,
    is_regenerate_intent,
    resolve_session_mode,
)

__all__ = [
    "SESSION_MODE_CONVERSE",
    "SESSION_MODE_INITIALIZE",
    "SESSION_MODE_REGENERATE",
    "MemoryPolicy",
    "SessionConfig",
    "SessionPolicy",
    "clear_checkpointer",
    "configure_checkpointer_from_env",
    "create_checkpointer",
    "extract_user_message",
    "get_checkpointer",
    "get_memory_policy",
    "get_session_policy",
    "is_regenerate_intent",
    "resolve_checkpointer_name",
    "resolve_session_mode",
    "set_checkpointer",
]
