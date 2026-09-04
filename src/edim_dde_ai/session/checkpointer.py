"""Process-wide LangGraph checkpointer registry."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CHECKPOINTER: Any | None = None
_PG_POOL: Any | None = None


def resolve_checkpointer_name(raw: str | None = None) -> str:
    """Normalize ``EDIM_CHECKPOINTER`` to ``memory`` or ``postgres``."""
    value = (
        raw if raw is not None else os.environ.get("EDIM_CHECKPOINTER", "memory")
    ).strip().lower()
    if value in {"", "memory", "mem", "inmemory", "none"}:
        return "memory"
    if value in {"postgres", "postgresql", "pg"}:
        return "postgres"
    raise ValueError(
        "Unknown checkpointer; expected memory|postgres via EDIM_CHECKPOINTER"
    )


def _close_pg_pool() -> None:
    global _PG_POOL
    pool = _PG_POOL
    _PG_POOL = None
    if pool is None:
        return
    try:
        pool.close()
    except Exception:  # noqa: BLE001 — best-effort shutdown
        logger.debug("Postgres checkpointer pool close failed", exc_info=True)


def _create_postgres_checkpointer(dsn: str) -> Any:
    """Build a durable PostgresSaver backed by a long-lived connection pool.

    ``PostgresSaver.from_conn_string`` is a context manager that closes the
    connection on exit — unsuitable for a FastAPI process. Use ``ConnectionPool``
    instead (LangGraph recommended pattern for servers).
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as exc:
        raise RuntimeError(
            "Postgres checkpointer requires langgraph-checkpoint-postgres. "
            "Install: pip install 'edim-dde-ai[postgres]'"
        ) from exc
    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise RuntimeError(
            "Postgres checkpointer requires psycopg and psycopg-pool. "
            "Install: pip install 'edim-dde-ai[postgres]'"
        ) from exc

    global _PG_POOL
    _close_pg_pool()
    pool = ConnectionPool(
        conninfo=dsn,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=True,
    )
    _PG_POOL = pool
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return checkpointer


def create_checkpointer(name: str | None = None, **kwargs: Any) -> Any:
    """Create a LangGraph checkpointer without installing it as process default.

    For ``postgres``, also retains a module-level connection pool so the saver
    stays usable for the process lifetime.
    """
    resolved = resolve_checkpointer_name(name)
    if resolved == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    if resolved == "postgres":
        from edim_dde_ai.store.connection_env import resolve_postgres_dsn

        dsn = kwargs.pop("dsn", None) or resolve_postgres_dsn(None)
        return _create_postgres_checkpointer(dsn)
    raise ValueError(f"Unknown checkpointer {resolved!r}")


def set_checkpointer(checkpointer: Any) -> None:
    """Install the process checkpointer."""
    global _CHECKPOINTER
    _CHECKPOINTER = checkpointer
    logger.info(
        "Checkpointer set to %s",
        type(checkpointer).__name__,
    )


def get_checkpointer() -> Any:
    """Return the configured checkpointer, defaulting to in-memory."""
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        _CHECKPOINTER = create_checkpointer("memory")
    return _CHECKPOINTER


def clear_checkpointer() -> None:
    """Reset to a fresh in-memory checkpointer (tests)."""
    global _CHECKPOINTER
    _close_pg_pool()
    _CHECKPOINTER = create_checkpointer("memory")


def configure_checkpointer_from_env(**kwargs: Any) -> Any:
    """Create and install the configured checkpointer."""
    checkpointer = create_checkpointer(None, **kwargs)
    set_checkpointer(checkpointer)
    return checkpointer
