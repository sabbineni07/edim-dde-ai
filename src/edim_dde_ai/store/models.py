"""Control-plane document models (backend-agnostic).

Business purpose
----------------
Every ``StateStore`` persists the same agent / session / audit shapes so the
API, CLI, and bootstrap sync stay backend-agnostic. Graph definitions remain
in Git; these records are catalog + runtime metadata only.

Public API
----------
* ``AgentRecord`` — durable agent catalog entry
* ``SessionRecord`` — multi-turn / HITL session state
* ``AuditEvent`` — append-oriented audit row
"""

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

    Attributes:
        agent_id: Stable agent identifier (matches YAML ``agent_id``).
        display_name: Human-facing name.
        version: Integer or string version from the definition.
        owner: Optional owner / team from YAML ``metadata``.
        risk_tier: ``low`` | ``medium`` | ``high`` (optional).
        lifecycle: ``draft`` | ``review`` | ``approved`` | ``deprecated``.
        hitl_required: Whether human-in-the-loop is required.
        source_path: Path to the loaded YAML file when known.
        git_sha: Build / deploy SHA when available.
        extra: Other YAML metadata keys.
        updated_at: ISO-8601 UTC timestamp.
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
        """Serialize to a plain dict (JSON-friendly).

        Returns:
            Field mapping suitable for JSONB / Cosmos / Redis payloads.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRecord:
        """Build a record from a dict; unknown keys fold into ``extra``.

        Args:
            data: Mapping from storage or wire format.

        Returns:
            Normalized ``AgentRecord``.
        """
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
    """Multi-turn / HITL session state keyed by session_id.

    Attributes:
        session_id: Stable session key.
        agent_id: Owning agent.
        status: ``open`` | ``waiting_hitl`` | ``closed``.
        state: Opaque runtime state bag for the graph / API.
        request_id: Optional correlating request id.
        extra: Host extensions.
        updated_at: ISO-8601 UTC timestamp.
    """

    session_id: str
    agent_id: str
    status: str = "open"  # open | waiting_hitl | closed
    state: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict.

        Returns:
            Field mapping suitable for persistence.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        """Build a session from a dict (known fields only).

        Args:
            data: Mapping from storage or wire format.

        Returns:
            Normalized ``SessionRecord``.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


@dataclass
class AuditEvent:
    """Append-oriented control-plane audit row.

    Attributes:
        event_id: Unique event key (UUID recommended).
        action: Action name (e.g. ``agent.upsert``).
        agent_id: Optional related agent.
        actor: Who performed the action (user, ``bootstrap``, …).
        detail: Structured payload.
        created_at: ISO-8601 UTC timestamp.
    """

    event_id: str
    action: str
    agent_id: str | None = None
    actor: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict.

        Returns:
            Field mapping suitable for persistence.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Build an audit event from a dict (known fields only).

        Args:
            data: Mapping from storage or wire format.

        Returns:
            Normalized ``AuditEvent``.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)
