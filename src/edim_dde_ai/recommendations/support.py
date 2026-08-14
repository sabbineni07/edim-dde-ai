"""Shared helpers for RecommendationStore backends (Template Method pieces)."""

from __future__ import annotations

from typing import Any

from edim_dde_ai.recommendations.models import RecommendationRecord


def filter_recommendation_rows(
    rows: list[RecommendationRecord],
    *,
    job_id: str | None = None,
    cluster_id: str | None = None,
    status: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
) -> list[RecommendationRecord]:
    """Apply optional filters and newest-first limit (memory / redis style)."""
    out = list(rows)
    if job_id is not None:
        out = [r for r in out if r.job_id == job_id]
    if cluster_id is not None:
        out = [r for r in out if r.cluster_id == cluster_id]
    if status is not None:
        out = [r for r in out if r.status == status]
    if agent_id is not None:
        out = [r for r in out if r.agent_id == agent_id]
    out.sort(key=lambda r: r.created_at, reverse=True)
    return out[: max(1, limit)]


class RecommendationStatusMixin:
    """Default ``update_status`` via get → with_status → save (Template Method).

    Backends that implement ``get`` / ``save`` inherit lifecycle transitions
    without duplicating validation (``RecommendationRecord.with_status``).
    """

    def get(self, recommendation_id: str) -> RecommendationRecord | None:  # pragma: no cover
        raise NotImplementedError

    def save(self, record: RecommendationRecord) -> RecommendationRecord:  # pragma: no cover
        raise NotImplementedError

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        current = self.get(recommendation_id)
        if current is None:
            return None
        return self.save(current.with_status(status))


def payload_as_dict(payload: Any) -> dict[str, Any]:
    """Normalize JSONB / SDK payloads to a plain dict."""
    import json

    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    return dict(payload)


def created_at_score(created_at: str) -> float:
    """ISO-8601 → Redis ZSET score (UTC timestamp); 0.0 on parse failure."""
    from datetime import datetime

    try:
        text = created_at.replace("Z", "+00:00")
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return 0.0
