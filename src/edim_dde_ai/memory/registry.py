"""Process-wide conversation store registry and backend factory."""

from __future__ import annotations

import os
from typing import Any

from edim_dde_ai.memory.memory_store import MemoryConversationStore
from edim_dde_ai.memory.protocols import ConversationStore

_STORE: ConversationStore = MemoryConversationStore()


def set_conversation_store(store: ConversationStore) -> None:
    """Install a conversation store for the current process."""
    global _STORE
    _STORE = store


def get_conversation_store() -> ConversationStore:
    """Return the process conversation store."""
    return _STORE


def clear_conversation_store() -> None:
    """Reset to the process-local store, primarily for tests."""
    global _STORE
    _STORE = MemoryConversationStore()


def resolve_conversation_store_name(raw: str | None = None) -> str:
    """Resolve the conversation backend, inheriting ``EDIM_STATE_STORE`` by default."""
    value = (
        raw
        if raw is not None
        else os.environ.get("EDIM_CONVERSATION_STORE")
        or os.environ.get("EDIM_STATE_STORE")
        or "memory"
    )
    value = value.strip().lower()
    if value in {"", "memory", "mem", "inmemory", "none"}:
        return "memory"
    if value in {"postgres", "postgresql", "pg"}:
        return "postgres"
    if value in {"lakebase"}:
        return "lakebase"
    if value in {"cosmos", "cosmosdb", "azure-cosmos"}:
        return "cosmos"
    if value == "redis":
        return "redis"
    raise ValueError(
        "Unknown conversation store; expected memory|postgres|lakebase|cosmos|redis"
    )


def create_conversation_store(
    name: str | None = None, **kwargs: Any
) -> ConversationStore:
    """Create a conversation store without installing it."""
    resolved = resolve_conversation_store_name(name)
    if resolved == "memory":
        return MemoryConversationStore()
    if resolved in {"postgres", "lakebase"}:
        from edim_dde_ai.memory.postgres import PostgresConversationStore

        dsn = kwargs.pop("dsn", None)
        if resolved == "lakebase" and dsn is None:
            dsn = os.environ.get("EDIM_LAKEBASE_DATABASE_URL")
        return PostgresConversationStore(dsn=dsn, name=resolved, **kwargs)
    if resolved == "redis":
        from edim_dde_ai.memory.redis_store import RedisConversationStore

        return RedisConversationStore(name=resolved, **kwargs)
    if resolved == "cosmos":
        from edim_dde_ai.memory.cosmos import CosmosConversationStore

        return CosmosConversationStore(**kwargs)
    raise ValueError(f"Unknown conversation store {resolved!r}")


def configure_conversation_store_from_env(**kwargs: Any) -> ConversationStore:
    """Create and install the configured conversation store."""
    store = create_conversation_store(None, **kwargs)
    set_conversation_store(store)
    return store
