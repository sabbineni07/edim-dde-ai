"""Process-wide LangGraph checkpointer registry."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CHECKPOINTER: Any | None = None


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


def create_checkpointer(name: str | None = None, **kwargs: Any) -> Any:
    """Create a LangGraph checkpointer without installing it."""
    resolved = resolve_checkpointer_name(name)
    if resolved == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    if resolved == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:
            raise RuntimeError(
                "Postgres checkpointer requires langgraph-checkpoint-postgres. "
                "Install: pip install 'edim-dde-ai[postgres]' langgraph-checkpoint-postgres"
            ) from exc
        from edim_dde_ai.store.connection_env import resolve_postgres_dsn

        dsn = kwargs.pop("dsn", None) or resolve_postgres_dsn(None)
        checkpointer = PostgresSaver.from_conn_string(dsn)
        if hasattr(checkpointer, "setup"):
            checkpointer.setup()
        return checkpointer
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
    _CHECKPOINTER = create_checkpointer("memory")


def configure_checkpointer_from_env(**kwargs: Any) -> Any:
    """Create and install the configured checkpointer."""
    checkpointer = create_checkpointer(None, **kwargs)
    set_checkpointer(checkpointer)
    return checkpointer
