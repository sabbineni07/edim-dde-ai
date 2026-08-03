"""In-memory state store (default / tests)."""

from __future__ import annotations

from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord


class MemoryStateStore:
    """Process-local dict store — no durability across restarts."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._sessions: dict[str, SessionRecord] = {}
        self._audit: list[AuditEvent] = []

    @property
    def name(self) -> str:
        return "memory"

    def ping(self) -> bool:
        return True

    def upsert_agent(self, record: AgentRecord) -> None:
        self._agents[record.agent_id] = record

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentRecord]:
        return sorted(self._agents.values(), key=lambda r: r.agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def upsert_session(self, record: SessionRecord) -> None:
        self._sessions[record.session_id] = record

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def append_audit(self, event: AuditEvent) -> None:
        self._audit.append(event)

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        rows = self._audit
        if agent_id is not None:
            rows = [e for e in rows if e.agent_id == agent_id]
        return list(reversed(rows[-limit:]))
