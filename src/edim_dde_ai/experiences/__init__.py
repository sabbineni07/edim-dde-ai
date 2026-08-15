"""Experience index — derived recommendation outcomes for similarity search.

Platform seam for future agents: register an ``ExperienceTransform`` per
``agent_id``, keep ``RecommendationStore`` as the system of record, and upsert
situation/action cards into a ``RetrievalProvider`` corpus.
"""

from edim_dde_ai.experiences.dedupe import (
    action_signature_from_hit,
    content_hash,
    dedupe_retrieval_hits,
)
from edim_dde_ai.experiences.indexing import (
    indexable_statuses,
    maybe_index_experience,
    upsert_experience_document,
)
from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.experiences.registry import (
    ExperienceIndexingStore,
    clear_experience_transforms,
    get_experience_transform,
    list_experience_transforms,
    register_experience_transform,
    wrap_recommendation_store,
)

__all__ = [
    "ExperienceDocument",
    "ExperienceIndexingStore",
    "action_signature_from_hit",
    "clear_experience_transforms",
    "content_hash",
    "dedupe_retrieval_hits",
    "get_experience_transform",
    "indexable_statuses",
    "list_experience_transforms",
    "maybe_index_experience",
    "register_experience_transform",
    "upsert_experience_document",
    "wrap_recommendation_store",
]
