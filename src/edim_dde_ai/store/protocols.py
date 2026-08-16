"""Strategy protocol for pluggable control-plane state stores.

Business purpose
----------------
Hosts inject a concrete ``StateStore`` at process start
(``configure_state_store_from_env`` or ``set_state_store``). API and CLI code
depend only on this protocol so unit tests can swap in ``MemoryStateStore``.

Public API
----------
* ``StateStore`` — agents / sessions / audit CRUD surface

Implementations: ``memory``, ``postgres``, ``cosmos``, ``redis``.
Graph YAML remains in Git; this store holds metadata and runtime session docs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord


@runtime_checkable
class StateStore(Protocol):
    """Backend for control-plane / app data (registries, sessions, audit).

    Implementations: memory, postgres, cosmos, redis.
    Graph YAML remains in Git; this store holds metadata and runtime session docs.
    """

    @property
    def name(self) -> str:
        """Stable backend id for health / logs.

        Returns:
            One of ``memory`` | ``postgres`` | ``cosmos`` | ``redis``.
        """

    def ping(self) -> bool:
        """Return whether the backend is reachable.

        Returns:
            ``True`` when a lightweight health check succeeds.
        """

    # --- Agents (catalog metadata) ---
    def upsert_agent(self, record: AgentRecord) -> None:
        """Insert or replace an agent catalog row.

        Args:
            record: Agent metadata (not the YAML graph body).
        """
        ...

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        """Fetch one agent by id.

        Args:
            agent_id: Stable agent identifier.

        Returns:
            ``AgentRecord`` or ``None`` if missing.
        """
        ...

    def list_agents(self) -> list[AgentRecord]:
        """List all agent catalog rows (implementation-defined order).

        Returns:
            Zero or more ``AgentRecord`` instances.
        """
        ...

    def delete_agent(self, agent_id: str) -> bool:
        """Remove an agent catalog row.

        Args:
            agent_id: Stable agent identifier.

        Returns:
            ``True`` if a row was removed.
        """
        ...

    # --- Sessions ---
    def upsert_session(self, record: SessionRecord) -> None:
        """Insert or replace a session document.

        Args:
            record: Multi-turn / HITL session state.
        """
        ...

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch one session by id.

        Args:
            session_id: Session key.

        Returns:
            ``SessionRecord`` or ``None`` if missing.
        """
        ...

    def delete_session(self, session_id: str) -> bool:
        """Remove a session document.

        Args:
            session_id: Session key.

        Returns:
            ``True`` if a row was removed.
        """
        ...

    # --- Audit ---
    def append_audit(self, event: AuditEvent) -> None:
        """Append an audit event (idempotent on ``event_id`` when possible).

        Args:
            event: Append-oriented audit row.
        """
        ...

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """List recent audit events (newest first when possible).

        Args:
            agent_id: Optional filter to one agent.
            limit: Maximum rows to return.

        Returns:
            Zero or more ``AuditEvent`` rows.
        """
        ...
