"""Experience index — derived recommendation outcomes for similarity search.

Business purpose
----------------
Agents persist product history as ``RecommendationRecord`` rows. Separately,
cross-entity learning needs **situation/action cards** in a retrieval corpus so
later runs can find feature-similar past outcomes (not exact entity-id matches).

This package is that **derived index seam**: domain packs register an
``ExperienceTransform`` per ``agent_id``; platform code upserts into the active
``RetrievalProvider`` without hard-coding agent field names.

How it fits the platform
------------------------
* ``RecommendationStore`` remains the system of record (lifecycle / history).
* ``ExperienceIndexingStore`` wraps store writes so save/status transitions
  also update (or delete) the experience corpus.
* Graph helpers call ``search_corpus`` (de-dupe + status boost).
* Phase 2: entity helpers and ``backfill_outcomes_from_store``.

Layers
------
* ``models`` / ``protocols`` / ``registry`` / ``indexing`` / ``dedupe``
* ``ranking`` — status boost for accepted/applied
* ``entity`` — subject-filtered store + experience search
* ``backfill`` — replay store rows into outcomes corpora

Public API
----------
* ``ExperienceDocument``, transform registry helpers
* ``maybe_index_experience``, ``upsert_experience_document``, ``indexable_statuses``
* ``dedupe_retrieval_hits``, ``apply_status_boost``, entity + backfill helpers
* ``wrap_recommendation_store``, ``ExperienceIndexingStore``
"""

from edim_dde_ai.experiences.backfill import BackfillResult, backfill_outcomes_from_store
from edim_dde_ai.experiences.dedupe import (
    action_signature_from_hit,
    content_hash,
    dedupe_retrieval_hits,
)
from edim_dde_ai.experiences.entity import (
    filter_hits_by_metadata,
    list_recommendations,
    search_experiences_for_entity,
)
from edim_dde_ai.experiences.indexing import (
    indexable_statuses,
    maybe_index_experience,
    upsert_experience_document,
)
from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.experiences.ranking import (
    DEFAULT_STATUS_BOOST,
    apply_status_boost,
    status_boost_for,
)
from edim_dde_ai.experiences.registry import (
    ExperienceIndexingStore,
    clear_experience_transforms,
    get_experience_transform,
    list_experience_transforms,
    register_experience_transform,
    wrap_recommendation_store,
)

__all__ = [
    "BackfillResult",
    "DEFAULT_STATUS_BOOST",
    "ExperienceDocument",
    "ExperienceIndexingStore",
    "action_signature_from_hit",
    "apply_status_boost",
    "backfill_outcomes_from_store",
    "clear_experience_transforms",
    "content_hash",
    "dedupe_retrieval_hits",
    "filter_hits_by_metadata",
    "get_experience_transform",
    "indexable_statuses",
    "list_experience_transforms",
    "list_recommendations",
    "maybe_index_experience",
    "register_experience_transform",
    "search_experiences_for_entity",
    "status_boost_for",
    "upsert_experience_document",
    "wrap_recommendation_store",
]
