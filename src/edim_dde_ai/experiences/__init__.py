"""Experience index — derived recommendation outcomes for similarity search.

Business purpose
----------------
Agents persist product history as ``RecommendationRecord`` rows. Separately,
cross-job learning needs **situation/action cards** in a retrieval corpus so
later runs can find feature-similar past outcomes (not exact ``job_id`` matches).

This package is that **derived index seam**: domain packs register an
``ExperienceTransform`` per ``agent_id``; platform code upserts into the active
``RetrievalProvider`` without hard-coding agent field names.

How it fits the platform
------------------------
* ``RecommendationStore`` remains the system of record (lifecycle / history).
* ``ExperienceIndexingStore`` wraps store writes so save/status transitions
  also update (or delete) the experience corpus.
* Graph / agent helpers call ``dedupe_retrieval_hits`` after ``search_corpus``.

Layers
------
* ``models`` — ``ExperienceDocument``
* ``protocols`` — ``ExperienceTransform`` strategy interface
* ``registry`` — transform map + ``ExperienceIndexingStore`` / wrap helper
* ``indexing`` — status-gated upsert / delete against RetrievalProvider
* ``dedupe`` — post-search collapse by id and action signature

Public API
----------
* ``ExperienceDocument``, transform registry helpers
* ``maybe_index_experience``, ``upsert_experience_document``, ``indexable_statuses``
* ``dedupe_retrieval_hits``, ``content_hash``, ``action_signature_from_hit``
* ``wrap_recommendation_store``, ``ExperienceIndexingStore``
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
