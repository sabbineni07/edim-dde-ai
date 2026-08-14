"""No-op recommendation store (persistence disabled)."""

from __future__ import annotations

from edim_dde_ai.recommendations.models import RecommendationRecord


class NoneRecommendationStore:
    """Discard writes; reads always empty. Use when history is intentionally off."""

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
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        return []

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        return None
