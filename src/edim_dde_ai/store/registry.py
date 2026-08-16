"""Process-wide state store registry and environment factory.

Business purpose
----------------
One ``StateStore`` per process (same pattern as Retrieval / WebSearch).
API lifespan calls ``configure_state_store_from_env()``; tests call
``set_state_store(MemoryStateStore())``. After loading agent YAML,
``sync_registered_agents_to_store`` upserts catalog rows + audit events.

Public API
----------
* ``set_state_store`` / ``get_state_store`` / ``clear_state_store``
* ``resolve_state_store_name`` / ``create_state_store`` /
  ``configure_state_store_from_env``
* ``agent_record_from_definition`` / ``sync_registered_agents_to_store``

Env
---
* ``EDIM_STATE_STORE`` — ``memory`` | ``postgres`` | ``cosmos`` | ``redis``
* ``EDIM_GIT_SHA`` / ``BUILD_SOURCEVERSION`` — stamped onto synced agents
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from edim_dde_ai.store.memory import MemoryStateStore
from edim_dde_ai.store.models import AgentRecord, AuditEvent
from edim_dde_ai.store.protocols import StateStore

logger = logging.getLogger(__name__)

_STORE: StateStore = MemoryStateStore()


def set_state_store(store: StateStore) -> None:
    """Replace the process-wide store (tests / custom host wiring).

    Args:
        store: Any object satisfying ``StateStore``.
    """
    global _STORE
    _STORE = store
    logger.info("State store set to %s", getattr(store, "name", type(store).__name__))


def get_state_store() -> StateStore:
    """Return the current process-wide store (never ``None``).

    Returns:
        The installed ``StateStore`` (defaults to ``MemoryStateStore``).
    """
    return _STORE


def clear_state_store() -> None:
    """Reset to a fresh ``MemoryStateStore`` (tests / re-bootstrap)."""
    global _STORE
    _STORE = MemoryStateStore()


def resolve_state_store_name(raw: str | None = None) -> str:
    """Normalize a backend name (or ``EDIM_STATE_STORE``) to a canonical id.

    Args:
        raw: Explicit name, or ``None`` to read ``EDIM_STATE_STORE``.

    Returns:
        One of ``memory`` | ``postgres`` | ``cosmos`` | ``redis``.

    Raises:
        ValueError: Unknown backend alias.
    """
    if raw is None:
        value = os.environ.get("EDIM_STATE_STORE", "").strip().lower()
    else:
        value = raw.strip().lower()
    if not value or value in {"memory", "mem", "inmemory", "none"}:
        return "memory"
    if value in {"postgres", "postgresql", "pg"}:
        return "postgres"
    if value in {"cosmos", "cosmosdb", "azure-cosmos"}:
        return "cosmos"
    if value in {"redis"}:
        return "redis"
    raise ValueError(
        f"Unknown EDIM_STATE_STORE={value!r}; expected memory|postgres|cosmos|redis"
    )


def create_state_store(name: str | None = None, **kwargs: Any) -> StateStore:
    """Factory for built-in backends (does not install into the process registry).

    Args:
        name: Backend name or alias; ``None`` uses ``EDIM_STATE_STORE``.
        **kwargs: Forwarded to the concrete constructor (e.g. ``dsn``,
            ``endpoint``).

    Returns:
        A new ``StateStore`` instance.

    Raises:
        ValueError: Unknown resolved backend name.
        RuntimeError: Missing optional deps or required env (from constructors).
    """
    resolved = resolve_state_store_name(name)
    if resolved == "memory":
        return MemoryStateStore()
    if resolved == "postgres":
        from edim_dde_ai.store.postgres import PostgresStateStore

        return PostgresStateStore(**kwargs)
    if resolved == "cosmos":
        from edim_dde_ai.store.cosmos import CosmosStateStore

        return CosmosStateStore(**kwargs)
    if resolved == "redis":
        from edim_dde_ai.store.redis_store import RedisStateStore

        return RedisStateStore(**kwargs)
    raise ValueError(f"Unknown state store {resolved!r}")


def configure_state_store_from_env(**kwargs: Any) -> StateStore:
    """Create store from ``EDIM_STATE_STORE`` and install it as the process default.

    Logs ping success/failure but does not raise on ping errors.

    Args:
        **kwargs: Forwarded to ``create_state_store``.

    Returns:
        The store that was installed (also via ``get_state_store``).
    """
    store = create_state_store(None, **kwargs)
    set_state_store(store)
    try:
        ok = store.ping()
        logger.info("State store %s ping=%s", store.name, ok)
    except Exception as exc:  # noqa: BLE001
        logger.warning("State store %s ping failed: %s", store.name, exc)
    return store


def agent_record_from_definition(definition: Any) -> AgentRecord:
    """Build an ``AgentRecord`` from an ``AgentDefinition`` (+ optional YAML metadata).

    Pulls ``owner`` / ``risk_tier`` / ``lifecycle`` / ``hitl_required`` from
    ``definition.raw["metadata"]`` when present. Stamps ``git_sha`` from
    ``EDIM_GIT_SHA`` or Azure DevOps ``BUILD_SOURCEVERSION``.

    Args:
        definition: Loaded agent definition (duck-typed: ``agent_id``,
            ``display_name``, ``version``, ``source_path``, ``raw``).

    Returns:
        Catalog ``AgentRecord`` ready for ``upsert_agent``.
    """
    raw = getattr(definition, "raw", None) or {}
    meta = raw.get("metadata") if isinstance(raw, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    return AgentRecord(
        agent_id=definition.agent_id,
        display_name=getattr(definition, "display_name", "") or definition.agent_id,
        version=getattr(definition, "version", 1),
        owner=meta.get("owner"),
        risk_tier=meta.get("risk_tier"),
        lifecycle=str(meta.get("lifecycle") or "draft"),
        hitl_required=bool(meta.get("hitl_required", False)),
        source_path=getattr(definition, "source_path", None),
        git_sha=os.environ.get("EDIM_GIT_SHA") or os.environ.get("BUILD_SOURCEVERSION"),
        extra={k: v for k, v in meta.items() if k not in {
            "owner", "risk_tier", "lifecycle", "hitl_required"
        }},
    )


def sync_registered_agents_to_store(
    *,
    store: StateStore | None = None,
    actor: str | None = None,
) -> int:
    """Upsert all in-process registered agents into the control-plane store.

    Call after ``bootstrap_agents()`` so Postgres/Cosmos catalogs match Git-loaded YAML.
    Returns number of agents synced.

    Args:
        store: Target store; defaults to ``get_state_store()``.
        actor: Audit actor string (default ``bootstrap``).

    Returns:
        Count of agents upserted.
    """
    from edim_dde_ai.registry.agents import get_agent_definition, list_agents

    target = store or get_state_store()
    count = 0
    for agent_id in list_agents():
        definition = get_agent_definition(agent_id)
        record = agent_record_from_definition(definition)
        target.upsert_agent(record)
        target.append_audit(
            AuditEvent(
                event_id=str(uuid.uuid4()),
                action="agent.upsert",
                agent_id=agent_id,
                actor=actor or "bootstrap",
                detail={
                    "version": record.version,
                    "lifecycle": record.lifecycle,
                    "source_path": record.source_path,
                },
            )
        )
        count += 1
    logger.info("Synced %s agents to state store %s", count, target.name)
    return count
