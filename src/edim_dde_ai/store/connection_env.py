"""Shared connection env helpers for StateStore and RecommendationStore.

Business purpose
----------------
Keeps Postgres / Cosmos / Redis DSN resolution in one place so control-plane
and recommendation backends stay plug-and-play with the same env knobs.

Public API
----------
* ``resolve_postgres_dsn`` — ``EDIM_DATABASE_URL`` / ``DATABASE_URL``
* ``resolve_cosmos_account`` — ``EDIM_COSMOS_*`` → ``(endpoint, key, database)``
* ``resolve_redis_settings`` — ``EDIM_REDIS_URL`` / ``EDIM_REDIS_PREFIX``
"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def resolve_postgres_dsn(dsn: str | None = None) -> str:
    """Return a postgresql:// DSN from argument or env.

    Args:
        dsn: Explicit DSN; when omitted, reads ``EDIM_DATABASE_URL`` then
            ``DATABASE_URL``.

    Returns:
        Non-empty DSN string with scheme ``postgresql`` or ``postgres``.

    Raises:
        RuntimeError: Missing URL or non-Postgres scheme.
    """
    value = (
        dsn
        or os.environ.get("EDIM_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if not value:
        raise RuntimeError(
            "Postgres backend requires EDIM_DATABASE_URL or DATABASE_URL"
        )
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise RuntimeError(
            f"EDIM_DATABASE_URL must be postgresql://… (got scheme={parsed.scheme!r})"
        )
    return value


def resolve_cosmos_account(
    *,
    endpoint: str | None = None,
    key: str | None = None,
    database: str | None = None,
) -> tuple[str, str, str]:
    """Return ``(endpoint, key, database_name)`` from args or ``EDIM_COSMOS_*``.

    Args:
        endpoint: Account URI; defaults to ``EDIM_COSMOS_ENDPOINT``.
        key: Account key; defaults to ``EDIM_COSMOS_KEY``.
        database: Database id; defaults to ``EDIM_COSMOS_DATABASE`` or ``edim``.

    Returns:
        Tuple of endpoint, key, and database name.

    Raises:
        RuntimeError: Missing endpoint or key.
    """
    ep = (endpoint or os.environ.get("EDIM_COSMOS_ENDPOINT") or "").strip()
    ky = (key or os.environ.get("EDIM_COSMOS_KEY") or "").strip()
    if not ep or not ky:
        raise RuntimeError(
            "Cosmos backend requires EDIM_COSMOS_ENDPOINT and EDIM_COSMOS_KEY"
        )
    db = (database or os.environ.get("EDIM_COSMOS_DATABASE") or "edim").strip()
    return ep, ky, db


def resolve_redis_settings(
    url: str | None = None, *, prefix: str | None = None
) -> tuple[str, str]:
    """Return ``(url, prefix)`` from args or ``EDIM_REDIS_URL`` / ``EDIM_REDIS_PREFIX``.

    Args:
        url: Redis URL; defaults to ``EDIM_REDIS_URL`` or
            ``redis://localhost:6379/0``.
        prefix: Key prefix; defaults to ``EDIM_REDIS_PREFIX`` or ``edim``.

    Returns:
        Tuple of resolved URL and key prefix.
    """
    resolved_url = (
        url or os.environ.get("EDIM_REDIS_URL") or "redis://localhost:6379/0"
    ).strip()
    resolved_prefix = (
        prefix or os.environ.get("EDIM_REDIS_PREFIX") or "edim"
    ).strip()
    return resolved_url, resolved_prefix
