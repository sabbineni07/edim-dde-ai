"""Recommendation lifecycle document models (backend-agnostic).

Business purpose
----------------
``RecommendationRecord`` is the product history row for agent recommendations:
who proposed what, optional entity ``subjects``, and lifecycle status.

Entity identity is agent-defined via ``subjects`` (e.g. ``job_id``,
``ticket_id``) — the framework does not reserve product field names.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

RECOMMENDATION_STATUSES = frozenset(
    {"proposed", "accepted", "rejected", "applied", "superseded"}
)


def _utc_now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_recommendation_id() -> str:
    """Allocate a new opaque recommendation id (UUID4 string)."""
    return str(uuid4())


@dataclass
class RecommendationRecord:
    """Persisted recommendation with lifecycle status (agent-agnostic).

    Attributes:
        recommendation_id: Stable primary key (also experience ``doc_id``).
        agent_id: Owning agent id (required).
        status: One of ``RECOMMENDATION_STATUSES``.
        subjects: Opaque entity keys for list filters / display
            (e.g. ``{"job_id": "...", "cluster_id": "..."}``).
        request_id / env / actor: Optional audit context.
        request / response: Opaque agent payloads.
        extra: Host escape hatch.
        created_at / updated_at: ISO-8601 UTC timestamps.
    """

    recommendation_id: str
    agent_id: str
    status: str = "proposed"
    subjects: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    env: str | None = None
    actor: str | None = None
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def subject(self, key: str, default: Any = None) -> Any:
        """Return one entity subject value (or ``default``)."""
        return (self.subjects or {}).get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / DB payload columns."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecommendationRecord:
        """Rehydrate from a dict, ignoring unknown keys.

        Legacy rows that stored ``job_id`` / ``cluster_id`` / ``job_run_id`` at
        the top level are folded into ``subjects``.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = dict(data)
        subjects = dict(payload.get("subjects") or {})
        for legacy in ("job_id", "cluster_id", "job_run_id"):
            if legacy in payload and legacy not in subjects:
                value = payload.pop(legacy)
                if value is not None and str(value) != "":
                    subjects[legacy] = value
            else:
                payload.pop(legacy, None)
        payload["subjects"] = subjects
        kwargs = {k: v for k, v in payload.items() if k in known}
        if "agent_id" not in kwargs or not str(kwargs.get("agent_id") or "").strip():
            kwargs["agent_id"] = str(kwargs.get("agent_id") or "unknown")
        return cls(**kwargs)

    def with_status(self, status: str) -> RecommendationRecord:
        """Return a copy with validated ``status`` and refreshed ``updated_at``."""
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
