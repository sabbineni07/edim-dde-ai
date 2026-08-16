"""In-memory recommendation store (tests / ephemeral local).

Business purpose
----------------
Process-local history that is fast and dependency-free. Ideal for unit tests
and short-lived local runs; data is lost on restart.

How it fits the platform
------------------------
Implements ``RecommendationStore`` via ``RecommendationStatusMixin`` for
shared ``update_status``. List filtering uses ``filter_recommendation_rows``.

Public API
----------
* ``MemoryRecommendationStore``
"""

from __future__ import annotations

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
        """Backend id ``memory``."""
        return "memory"

    def ping(self) -> bool:
        """Always healthy (no remote dependency)."""
        return True

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        """Insert or replace by ``recommendation_id``.

        Args:
            record: Full recommendation document.

        Returns:
            The same ``record`` (stored by reference in the process map).
        """
        self._rows[record.recommendation_id] = record
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        """Fetch one recommendation by id, or ``None``."""
        return self._rows.get(recommendation_id)

    def list(
        self,
        *,
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        """List newest-first with optional exact-match filters.

        Args:
            job_id / cluster_id / status / agent_id: Exact filters when set.
            limit: Max rows (clamped to at least 1).

        Returns:
            Filtered records sorted by ``created_at`` descending.
        """
        return filter_recommendation_rows(
            list(self._rows.values()),
            job_id=job_id,
            cluster_id=cluster_id,
            status=status,
            agent_id=agent_id,
            limit=limit,
        )
