"""Pluggable recommendation lifecycle / history stores.

Business purpose
----------------
Agents produce recommendations that engineers accept, reject, apply, or
supersede. This package persists that **product history** separately from
control-plane catalog/session state (``edim_dde_ai.store``).

How it fits the platform
------------------------
* Strategy backends: ``none`` · ``memory`` · ``postgres`` · ``cosmos`` · ``redis``
* Process registry + env factory mirror ``StateStore`` so local Compose and
  deployed Cosmos stay aligned (``EDIM_RECOMMENDATION_STORE`` can inherit
  ``EDIM_STATE_STORE``).
* ``set_recommendation_store`` wraps the backend with
  ``ExperienceIndexingStore`` so experience-index upserts stay orthogonal.

Layers
------
* ``models`` — ``RecommendationRecord``, statuses, id helper
* ``protocols`` — ``RecommendationStore`` interface
* ``support`` — shared filter / status mixin / payload helpers
* ``none_store`` / ``memory`` / ``postgres`` / ``cosmos`` / ``redis_store``
* ``registry`` — get/set + ``create_*`` / ``configure_*_from_env``

Public API
----------
Eager imports below; optional heavy backends via ``__getattr__``
(``PostgresRecommendationStore``, ``CosmosRecommendationStore``,
``RedisRecommendationStore``).
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
    """Lazy-load optional backend classes (postgres / cosmos / redis extras)."""
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
