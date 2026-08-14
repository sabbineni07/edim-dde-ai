"""Recommendation lifecycle document models (backend-agnostic)."""

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
    return datetime.now(timezone.utc).isoformat()


def new_recommendation_id() -> str:
    return str(uuid4())


@dataclass
class RecommendationRecord:
    """Persisted cluster-tuning (or future) recommendation with lifecycle status.

    Source of truth for *how* the agent decided remains the request/response
    payloads and LangSmith traces; this record is the product history row.
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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecommendationRecord:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def with_status(self, status: str) -> RecommendationRecord:
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
