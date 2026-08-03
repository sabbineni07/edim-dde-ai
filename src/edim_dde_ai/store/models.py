"""Control-plane document models (backend-agnostic)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentRecord:
    """Durable agent catalog entry (metadata — not the YAML graph itself).

    Source of truth for graph definition remains Git / Azure DevOps ``*.agent.yaml``.
    This record tracks ownership, lifecycle, and pointers for the control plane.
    """

    agent_id: str
    display_name: str = ""
    version: int | str = 1
    owner: str | None = None
    risk_tier: str | None = None  # low | medium | high
    lifecycle: str = "draft"  # draft | review | approved | deprecated
    hitl_required: bool = False
    source_path: str | None = None
    git_sha: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRecord:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        if "extra" in data and isinstance(data["extra"], dict):
            kwargs["extra"] = dict(data["extra"])
        elif "extra" not in kwargs:
            kwargs["extra"] = {
                k: v for k, v in data.items() if k not in known and k != "id"
            }
        return cls(**kwargs)


@dataclass
class SessionRecord:
    """Multi-turn / HITL session state keyed by session_id."""

    session_id: str
    agent_id: str
    status: str = "open"  # open | waiting_hitl | closed
    state: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


@dataclass
class AuditEvent:
    """Append-oriented control-plane audit row."""

    event_id: str
    action: str
    agent_id: str | None = None
    actor: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)
