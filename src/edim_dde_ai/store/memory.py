"""In-memory state store (default / tests).

Business purpose
----------------
Default ``StateStore`` when ``EDIM_STATE_STORE`` is unset or ``memory``. No
durability across restarts — suitable for unit tests and ephemeral local runs.

Public API
----------
* ``MemoryStateStore`` — process-local agents / sessions / audit
"""

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
        """Backend id for health / logs (``memory``)."""
        return "memory"

    def ping(self) -> bool:
        """Always healthy (in-process).

        Returns:
            ``True``.
        """
        return True

    def upsert_agent(self, record: AgentRecord) -> None:
        """Insert or replace an agent by ``agent_id``.

        Args:
            record: Agent catalog row.
        """
        self._agents[record.agent_id] = record

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        """Fetch one agent.

        Args:
            agent_id: Agent key.

        Returns:
            ``AgentRecord`` or ``None``.
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentRecord]:
        """List agents sorted by ``agent_id``.

        Returns:
            Sorted agent rows.
        """
        return sorted(self._agents.values(), key=lambda r: r.agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        """Remove an agent if present.

        Args:
            agent_id: Agent key.

        Returns:
            ``True`` if removed.
        """
        return self._agents.pop(agent_id, None) is not None

    def upsert_session(self, record: SessionRecord) -> None:
        """Insert or replace a session by ``session_id``.

        Args:
            record: Session document.
        """
        self._sessions[record.session_id] = record

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch one session.

        Args:
            session_id: Session key.

        Returns:
            ``SessionRecord`` or ``None``.
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Remove a session if present.

        Args:
            session_id: Session key.

        Returns:
            ``True`` if removed.
        """
        return self._sessions.pop(session_id, None) is not None

    def append_audit(self, event: AuditEvent) -> None:
        """Append an audit event to the in-memory list.

        Args:
            event: Audit row.
        """
        self._audit.append(event)

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """Return recent audit events (newest first).

        Args:
            agent_id: Optional filter.
            limit: Maximum rows.

        Returns:
            Up to ``limit`` events, newest first.
        """
        rows = self._audit
        if agent_id is not None:
            rows = [e for e in rows if e.agent_id == agent_id]
        return list(reversed(rows[-limit:]))
