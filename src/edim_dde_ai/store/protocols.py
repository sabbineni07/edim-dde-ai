"""Pluggable control-plane state store protocol."""

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
        """Stable id: ``memory`` | ``postgres`` | ``cosmos`` | ``redis``."""

    def ping(self) -> bool:
        """Return True if the backend is reachable."""

    # --- Agents (catalog metadata) ---
    def upsert_agent(self, record: AgentRecord) -> None: ...

    def get_agent(self, agent_id: str) -> AgentRecord | None: ...

    def list_agents(self) -> list[AgentRecord]: ...

    def delete_agent(self, agent_id: str) -> bool: ...

    # --- Sessions ---
    def upsert_session(self, record: SessionRecord) -> None: ...

    def get_session(self, session_id: str) -> SessionRecord | None: ...

    def delete_session(self, session_id: str) -> bool: ...

    # --- Audit ---
    def append_audit(self, event: AuditEvent) -> None: ...

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]: ...
