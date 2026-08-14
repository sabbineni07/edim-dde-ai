"""Pluggable recommendation history store protocol (Strategy)."""

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
        """Stable id matching the backend."""

    def ping(self) -> bool:
        """Return True if the backend is reachable (``none`` always True)."""

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        """Insert or replace by ``recommendation_id``; return stored record."""

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        """Fetch one recommendation by id."""

    def list(
        self,
        *,
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        """List newest-first, optionally filtered."""

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        """Transition lifecycle status; return updated record or None if missing."""
