"""Process-wide recommendation store registry + env factory (Factory Method).

Business purpose
----------------
One recommendation store per process (same pattern as StateStore / web search).
API lifespan calls ``configure_recommendation_store_from_env()``; tests call
``set_recommendation_store(MemoryRecommendationStore())``.

How it fits the platform
------------------------
``set_recommendation_store`` always runs ``wrap_recommendation_store`` so
experience-index hooks attach for every non-``none`` backend.

Env vars
--------
* ``EDIM_RECOMMENDATION_STORE`` — ``none`` | ``memory`` | ``postgres`` |
  ``cosmos`` | ``redis`` | ``auto`` (inherit ``EDIM_STATE_STORE``)
* Backend-specific connection vars are shared with StateStore
  (``EDIM_DATABASE_URL``, Cosmos, Redis) where applicable.

Public API
----------
* ``set_recommendation_store`` / ``get_recommendation_store`` /
  ``clear_recommendation_store``
* ``resolve_recommendation_store_name`` / ``create_recommendation_store`` /
  ``configure_recommendation_store_from_env``
"""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.recommendations.memory import MemoryRecommendationStore
from edim_dde_ai.recommendations.none_store import NoneRecommendationStore
from edim_dde_ai.recommendations.protocols import RecommendationStore
from edim_dde_ai.store.registry import resolve_state_store_name

logger = logging.getLogger(__name__)

_STORE: RecommendationStore = NoneRecommendationStore()


def set_recommendation_store(store: RecommendationStore) -> None:
    """Replace the process-wide store (wraps with experience indexing).

    Args:
        store: Any object satisfying ``RecommendationStore``. ``none`` backends
            are left unwrapped; others get ``ExperienceIndexingStore``.
    """
    global _STORE
    from edim_dde_ai.experiences.registry import wrap_recommendation_store

    wrapped = wrap_recommendation_store(store)
    _STORE = wrapped
    logger.info(
        "Recommendation store set to %s",
        getattr(wrapped, "name", type(wrapped).__name__),
    )


def get_recommendation_store() -> RecommendationStore:
    """Return the current process-wide store (never ``None``)."""
    return _STORE


def clear_recommendation_store() -> None:
    """Reset to ``NoneRecommendationStore`` (tests / teardown)."""
    global _STORE
    _STORE = NoneRecommendationStore()


def resolve_recommendation_store_name(raw: str | None = None) -> str:
    """Normalize ``EDIM_RECOMMENDATION_STORE``.

    When unset/empty, follows ``EDIM_STATE_STORE`` so local Compose
    (postgres) and deployed Cosmos stay aligned without a second knob.
    Explicit ``none`` disables persistence.

    Args:
        raw: Override string; ``None`` reads the environment.

    Returns:
        Canonical backend name: ``none`` | ``memory`` | ``postgres`` |
        ``cosmos`` | ``redis``.

    Raises:
        ValueError: Unknown backend token.
    """
    if raw is None:
        value = os.environ.get("EDIM_RECOMMENDATION_STORE", "").strip().lower()
    else:
        value = raw.strip().lower()
    if value in {"none", "off", "disabled", "false", "0"}:
        return "none"
    if not value or value in {"auto", "same", "inherit"}:
        return resolve_state_store_name(None)
    if value in {"memory", "mem", "inmemory"}:
        return "memory"
    if value in {"postgres", "postgresql", "pg"}:
        return "postgres"
    if value in {"cosmos", "cosmosdb", "azure-cosmos"}:
        return "cosmos"
    if value in {"redis"}:
        return "redis"
    raise ValueError(
        f"Unknown EDIM_RECOMMENDATION_STORE={value!r}; "
        "expected none|memory|postgres|cosmos|redis|auto"
    )


def create_recommendation_store(
    name: str | None = None, **kwargs: Any
) -> RecommendationStore:
    """Factory for built-in recommendation backends.

    Args:
        name: Backend name or alias; ``None`` uses env / StateStore inherit.
        **kwargs: Forwarded to the concrete constructor (DSN, Cosmos keys, …).

    Returns:
        Unwrapped concrete store (caller usually installs via
        ``set_recommendation_store`` / ``configure_recommendation_store_from_env``).

    Raises:
        ValueError: Unknown resolved backend name.
        RuntimeError: Missing optional dependency for the chosen backend.
    """
    resolved = resolve_recommendation_store_name(name)
    if resolved == "none":
        return NoneRecommendationStore()
    if resolved == "memory":
        return MemoryRecommendationStore()
    if resolved == "postgres":
        from edim_dde_ai.recommendations.postgres import PostgresRecommendationStore

        return PostgresRecommendationStore(**kwargs)
    if resolved == "cosmos":
        from edim_dde_ai.recommendations.cosmos import CosmosRecommendationStore

        return CosmosRecommendationStore(**kwargs)
    if resolved == "redis":
        from edim_dde_ai.recommendations.redis_store import RedisRecommendationStore

        return RedisRecommendationStore(**kwargs)
    raise ValueError(f"Unknown recommendation store {resolved!r}")


def configure_recommendation_store_from_env(**kwargs: Any) -> RecommendationStore:
    """Create store from ``EDIM_RECOMMENDATION_STORE`` (or inherit StateStore) and install.

    Args:
        **kwargs: Forwarded to ``create_recommendation_store``.

    Returns:
        The store that was installed (also available via
        ``get_recommendation_store``).
    """
    store = create_recommendation_store(None, **kwargs)
    set_recommendation_store(store)
    try:
        ok = store.ping()
        logger.info("Recommendation store %s ping=%s", store.name, ok)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Recommendation store %s ping failed: %s", store.name, exc)
    return store
