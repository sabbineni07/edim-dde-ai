"""In-memory recommendation store (tests / ephemeral local)."""

from __future__ import annotations

from typing import Any, Mapping

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.support import (
    RecommendationStatusMixin,
    filter_recommendation_rows,
)


class MemoryRecommendationStore(RecommendationStatusMixin):
    """Process-local recommendation history (lost on restart)."""

    def __init__(self) -> None:
        self._rows: dict[str, RecommendationRecord] = {}

    @property
    def name(self) -> str:
        return "memory"

    def ping(self) -> bool:
        return True

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        self._rows[record.recommendation_id] = record
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        return self._rows.get(recommendation_id)

    def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        subjects: Mapping[str, Any] | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        return filter_recommendation_rows(
            list(self._rows.values()),
            subjects=subjects,
            status=status,
            agent_id=agent_id,
            limit=limit,
        )
