"""ExperienceTransform — Strategy for domain-specific index parsing."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.recommendations.models import RecommendationRecord


@runtime_checkable
class ExperienceTransform(Protocol):
    """Turn a RecommendationRecord into an ExperienceDocument (or skip).

    Domain packs register one transform per ``agent_id``. Platform code never
    hard-codes cluster-tuning field names.
    """

    @property
    def agent_id(self) -> str: ...

    @property
    def corpus(self) -> str: ...

    def transform(self, record: RecommendationRecord) -> ExperienceDocument | None: ...
