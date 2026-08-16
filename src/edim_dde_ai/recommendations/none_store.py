"""No-op recommendation store (persistence disabled).

Business purpose
----------------
Null Object when product history is intentionally off
(``EDIM_RECOMMENDATION_STORE=none``). Writes are discarded; reads are empty.

How it fits the platform
------------------------
Default process registry value before ``configure_recommendation_store_from_env``.
``wrap_recommendation_store`` leaves this backend unwrapped (no experience index).

Public API
----------
* ``NoneRecommendationStore`` — ``name == "none"``
"""

from __future__ import annotations

from edim_dde_ai.recommendations.models import RecommendationRecord


class NoneRecommendationStore:
    """Discard writes; reads always empty. Use when history is intentionally off."""

    @property
    def name(self) -> str:
        """Backend id ``none``."""
        return "none"

    def ping(self) -> bool:
        """Always healthy (no remote dependency)."""
        return True

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        """Return ``record`` unchanged without persisting.

        Args:
            record: Recommendation that would have been stored.

        Returns:
            The same ``record`` instance/value passed in.
        """
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        """Always ``None`` (nothing is stored)."""
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
        """Always an empty list (filters ignored)."""
        return []

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        """Always ``None`` (no row to update)."""
        return None
