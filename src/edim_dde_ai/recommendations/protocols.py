"""Pluggable recommendation history store protocol (Strategy).

Business purpose
----------------
Hosts inject a concrete ``RecommendationStore`` at process start. API and
agents depend only on this protocol so tests can use ``memory`` and production
can use postgres/cosmos/redis without code changes.

How it fits the platform
------------------------
Parallel to ``StateStore`` (catalog/sessions/audit) — same plug-and-play idea,
separate concern so product history does not overload control-plane catalog APIs.

Public API
----------
* ``RecommendationStore`` — ``name``, ``ping``, ``save``, ``get``, ``list``,
  ``update_status``
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.recommendations.models import RecommendationRecord


@runtime_checkable
class RecommendationStore(Protocol):
    """Backend for recommendation lifecycle / history documents.

    Parallel to ``StateStore`` (catalog/sessions/audit) — same plug-and-play
    idea, separate concern so product history does not overload control-plane
    catalog APIs.

    Implementations: ``none`` | ``memory`` | ``postgres`` | ``cosmos`` | ``redis``.
    """

    @property
    def name(self) -> str:
        """Stable id matching the backend (``memory``, ``postgres``, …)."""

    def ping(self) -> bool:
        """Return True if the backend is reachable (``none`` always True)."""

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        """Insert or replace by ``recommendation_id``; return stored record.

        Args:
            record: Full recommendation document to persist.

        Returns:
            The record as stored (may be identical to input).
        """

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        """Fetch one recommendation by id.

        Args:
            recommendation_id: Primary key.

        Returns:
            The record, or ``None`` if missing.
        """

    def list(
        self,
        *,
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        """List newest-first, optionally filtered.

        Args:
            job_id: Exact match filter when set.
            cluster_id: Exact match filter when set.
            status: Exact match filter when set.
            agent_id: Exact match filter when set.
            limit: Max rows (backends clamp to at least 1).

        Returns:
            Records ordered by ``created_at`` descending.
        """

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        """Transition lifecycle status; return updated record or None if missing.

        Args:
            recommendation_id: Target row.
            status: New status (validated by ``RecommendationRecord.with_status``
                on mixin-based backends).

        Returns:
            Updated record, or ``None`` if the id does not exist.
        """
