"""Pluggable recommendation lifecycle / history stores.

Strategy backends: ``none`` · ``memory`` · ``postgres`` · ``cosmos`` · ``redis``.
Factory + process registry mirror ``edim_dde_ai.store`` (control-plane StateStore).
"""

from edim_dde_ai.recommendations.memory import MemoryRecommendationStore
from edim_dde_ai.recommendations.models import (
    RECOMMENDATION_STATUSES,
    RecommendationRecord,
    new_recommendation_id,
)
from edim_dde_ai.recommendations.none_store import NoneRecommendationStore
from edim_dde_ai.recommendations.protocols import RecommendationStore
from edim_dde_ai.recommendations.registry import (
    clear_recommendation_store,
    configure_recommendation_store_from_env,
    create_recommendation_store,
    get_recommendation_store,
    resolve_recommendation_store_name,
    set_recommendation_store,
)

__all__ = [
    "RecommendationStore",
    "RecommendationRecord",
    "RECOMMENDATION_STATUSES",
    "new_recommendation_id",
    "NoneRecommendationStore",
    "MemoryRecommendationStore",
    "set_recommendation_store",
    "get_recommendation_store",
    "clear_recommendation_store",
    "create_recommendation_store",
    "configure_recommendation_store_from_env",
    "resolve_recommendation_store_name",
]


def __getattr__(name: str):
    if name == "PostgresRecommendationStore":
        from edim_dde_ai.recommendations.postgres import PostgresRecommendationStore

        return PostgresRecommendationStore
    if name == "CosmosRecommendationStore":
        from edim_dde_ai.recommendations.cosmos import CosmosRecommendationStore

        return CosmosRecommendationStore
    if name == "RedisRecommendationStore":
        from edim_dde_ai.recommendations.redis_store import RedisRecommendationStore

        return RedisRecommendationStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
