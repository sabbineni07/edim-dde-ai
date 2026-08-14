"""Process-wide recommendation store registry + env factory (Factory Method)."""

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
    global _STORE
    _STORE = store
    logger.info(
        "Recommendation store set to %s", getattr(store, "name", type(store).__name__)
    )


def get_recommendation_store() -> RecommendationStore:
    return _STORE


def clear_recommendation_store() -> None:
    global _STORE
    _STORE = NoneRecommendationStore()


def resolve_recommendation_store_name(raw: str | None = None) -> str:
    """Normalize ``EDIM_RECOMMENDATION_STORE``.

    When unset/empty, follows ``EDIM_STATE_STORE`` so local Compose
    (postgres) and deployed Cosmos stay aligned without a second knob.
    Explicit ``none`` disables persistence.
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
    """Factory for built-in recommendation backends."""
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
    """Create store from ``EDIM_RECOMMENDATION_STORE`` (or inherit StateStore) and install."""
    store = create_recommendation_store(None, **kwargs)
    set_recommendation_store(store)
    try:
        ok = store.ping()
        logger.info("Recommendation store %s ping=%s", store.name, ok)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Recommendation store %s ping failed: %s", store.name, exc)
    return store
