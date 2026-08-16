"""Strategy protocol for domain-specific experience-index transforms.

Business purpose
----------------
Each agent pack knows how to turn its ``RecommendationRecord`` payloads into
an ``ExperienceDocument`` (or skip). Platform indexing code only calls this
protocol so field names stay in the domain layer.

How it fits the platform
------------------------
Domain bootstrap registers one transform per ``agent_id`` via
``register_experience_transform``. ``maybe_index_experience`` looks up the
transform by ``record.agent_id`` and uses ``corpus`` for the RetrievalProvider.

Public API
----------
* ``ExperienceTransform`` — ``agent_id``, ``corpus``, ``transform``
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.recommendations.models import RecommendationRecord


@runtime_checkable
class ExperienceTransform(Protocol):
    """Turn a RecommendationRecord into an ExperienceDocument (or skip).

    Domain packs register one transform per ``agent_id``. Platform code never
    hard-codes cluster-tuning / spark_rca field names.

    Implementations should return ``None`` when the record is not indexable
    (wrong status, empty body, insufficient features) rather than raising.
    """

    @property
    def agent_id(self) -> str:
        """Agent id this transform owns (must match ``RecommendationRecord.agent_id``)."""
        ...

    @property
    def corpus(self) -> str:
        """Retrieval corpus name for upserts / deletes."""
        ...

    def transform(self, record: RecommendationRecord) -> ExperienceDocument | None:
        """Build an experience card, or ``None`` to skip indexing.

        Args:
            record: Persisted recommendation lifecycle row.

        Returns:
            ``ExperienceDocument`` ready for upsert, or ``None`` to no-op.
        """
        ...
