"""Pluggable control-plane state stores (memory · postgres · cosmos · redis)."""

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
