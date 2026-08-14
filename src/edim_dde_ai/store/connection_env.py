"""Shared connection env helpers for StateStore and RecommendationStore.

Keeps Postgres / Cosmos / Redis DSN resolution in one place so control-plane
and recommendation backends stay plug-and-play with the same env knobs.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def resolve_postgres_dsn(dsn: str | None = None) -> str:
    """Return a postgresql:// DSN from argument or ``EDIM_DATABASE_URL`` / ``DATABASE_URL``."""
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
    """Return ``(endpoint, key, database_name)`` from args or ``EDIM_COSMOS_*``."""
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
    """Return ``(url, prefix)`` from args or ``EDIM_REDIS_URL`` / ``EDIM_REDIS_PREFIX``."""
    resolved_url = (
        url or os.environ.get("EDIM_REDIS_URL") or "redis://localhost:6379/0"
    ).strip()
    resolved_prefix = (
        prefix or os.environ.get("EDIM_REDIS_PREFIX") or "edim"
    ).strip()
    return resolved_url, resolved_prefix
