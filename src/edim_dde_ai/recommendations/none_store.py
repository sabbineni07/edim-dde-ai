"""No-op recommendation store (persistence disabled)."""

from __future__ import annotations

from typing import Any, Mapping

from edim_dde_ai.recommendations.models import RecommendationRecord


class NoneRecommendationStore:
    """Discard writes; reads always empty."""

    @property
    def name(self) -> str:
        return "none"

    def ping(self) -> bool:
        return True

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        return None

    def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        subjects: Mapping[str, Any] | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        return []

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        return None
