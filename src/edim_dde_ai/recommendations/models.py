"""Recommendation lifecycle document models (backend-agnostic).

Business purpose
----------------
``RecommendationRecord`` is the product history row for agent recommendations:
who proposed what, for which job/cluster, and the current lifecycle status.

How it fits the platform
------------------------
Stores persist this shape; experience indexing derives search cards from it.
Source of truth for *how* the agent decided remains request/response payloads
and LangSmith traces — this record is the durable product history.

Public API
----------
* ``RECOMMENDATION_STATUSES`` — allowed lifecycle values
* ``new_recommendation_id`` — UUID helper
* ``RecommendationRecord`` — dataclass + serialize / status transition
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# proposed → accepted | rejected | applied | superseded
RECOMMENDATION_STATUSES = frozenset(
    {"proposed", "accepted", "rejected", "applied", "superseded"}
)


def _utc_now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_recommendation_id() -> str:
    """Allocate a new opaque recommendation id (UUID4 string).

    Returns:
        Fresh id suitable for ``RecommendationRecord.recommendation_id``.
    """
    return str(uuid4())


@dataclass
class RecommendationRecord:
    """Persisted cluster-tuning (or future) recommendation with lifecycle status.

    Source of truth for *how* the agent decided remains the request/response
    payloads and LangSmith traces; this record is the product history row.

    Attributes:
        recommendation_id: Stable primary key (also experience ``doc_id``).
        agent_id: Owning agent (default ``cluster_tuning``).
        status: One of ``RECOMMENDATION_STATUSES``.
        job_id / cluster_id / job_run_id / request_id / env / actor: Optional
            entity and audit context for list filters and UI.
        request / response: Opaque agent payloads (dicts).
        extra: Escape hatch for host-specific fields.
        created_at / updated_at: ISO-8601 UTC timestamps.
    """

    recommendation_id: str
    agent_id: str = "cluster_tuning"
    status: str = "proposed"
    job_id: str | None = None
    cluster_id: str | None = None
    job_run_id: str | None = None
    request_id: str | None = None
    env: str | None = None
    actor: str | None = None
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / DB payload columns."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecommendationRecord:
        """Rehydrate from a dict, ignoring unknown keys.

        Args:
            data: Serialized record (e.g. from JSONB or Cosmos item).

        Returns:
            A new ``RecommendationRecord`` using only known dataclass fields.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def with_status(self, status: str) -> RecommendationRecord:
        """Return a copy with validated ``status`` and refreshed ``updated_at``.

        Args:
            status: New lifecycle status (case-insensitive).

        Returns:
            New record instance (does not mutate ``self``).

        Raises:
            ValueError: Status not in ``RECOMMENDATION_STATUSES``.
        """
        status = str(status).strip().lower()
        if status not in RECOMMENDATION_STATUSES:
            raise ValueError(
                f"Invalid recommendation status {status!r}; "
                f"expected one of {sorted(RECOMMENDATION_STATUSES)}"
            )
        return RecommendationRecord(
            **{
                **self.to_dict(),
                "status": status,
                "updated_at": _utc_now(),
            }
        )
