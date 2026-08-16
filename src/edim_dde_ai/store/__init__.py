"""Pluggable control-plane state stores (memory · postgres · cosmos · redis).

Business purpose
----------------
The control plane needs durable (or process-local) storage for agent catalog
metadata, multi-turn / HITL sessions, and audit events. Graph YAML stays in
Git; this package holds **runtime registry documents**. Domain code depends on
``StateStore`` — never on Postgres/Cosmos/Redis SDKs directly.

Public API
----------
* ``StateStore`` — strategy protocol
* ``AgentRecord`` / ``SessionRecord`` / ``AuditEvent`` — document models
* ``MemoryStateStore`` — always-importable default
* Registry — ``configure_state_store_from_env``, ``get_state_store``,
  ``sync_registered_agents_to_store``, …

Heavy backends (``PostgresStateStore``, ``CosmosStateStore``,
``RedisStateStore``) are lazy via ``__getattr__``.

Env
---
* ``EDIM_STATE_STORE`` — ``memory`` | ``postgres`` | ``cosmos`` | ``redis``
  (see ``registry.resolve_state_store_name``)
"""

from edim_dde_ai.store.memory import MemoryStateStore
from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord
from edim_dde_ai.store.protocols import StateStore
from edim_dde_ai.store.registry import (
    agent_record_from_definition,
    clear_state_store,
    configure_state_store_from_env,
    create_state_store,
    get_state_store,
    resolve_state_store_name,
    set_state_store,
    sync_registered_agents_to_store,
)

__all__ = [
    "StateStore",
    "AgentRecord",
    "SessionRecord",
    "AuditEvent",
    "MemoryStateStore",
    "set_state_store",
    "get_state_store",
    "clear_state_store",
    "create_state_store",
    "configure_state_store_from_env",
    "resolve_state_store_name",
    "agent_record_from_definition",
    "sync_registered_agents_to_store",
]


def __getattr__(name: str):
    """Lazy-load optional state-store backends (avoids hard deps at import time)."""
    if name == "PostgresStateStore":
        from edim_dde_ai.store.postgres import PostgresStateStore

        return PostgresStateStore
    if name == "CosmosStateStore":
        from edim_dde_ai.store.cosmos import CosmosStateStore

        return CosmosStateStore
    if name == "RedisStateStore":
        from edim_dde_ai.store.redis_store import RedisStateStore

        return RedisStateStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
