"""Redis state store (sessions / cache-oriented; optional catalog).

Business purpose
----------------
Ephemeral sessions and local cache via Redis hashes + a capped audit list.
Prefer Postgres/Cosmos as the system of record for agent catalog in production.

Public API
----------
* ``RedisStateStore`` — ``StateStore`` over prefixed Redis keys

Install: ``pip install 'edim-dde-ai[redis]'``

Env
---
* ``EDIM_REDIS_URL`` — default ``redis://localhost:6379/0``
* ``EDIM_REDIS_PREFIX`` — key prefix (default ``edim``)
* ``EDIM_REDIS_AUDIT_MAX`` — max audit entries retained (default ``1000``)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from edim_dde_ai.store.connection_env import resolve_redis_settings
from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord

logger = logging.getLogger(__name__)


class RedisStateStore:
    """Control-plane store using Redis hashes + a capped audit list.

    Good for ephemeral sessions and local cache. Prefer Postgres/Cosmos as the
    system of record for agent catalog in production.

    Install: ``pip install 'edim-dde-ai[redis]'``

    Env:
      - ``EDIM_REDIS_URL`` — default ``redis://localhost:6379/0``
      - ``EDIM_REDIS_PREFIX`` — key prefix (default ``edim``)
      - ``EDIM_REDIS_AUDIT_MAX`` — max audit entries retained (default ``1000``)
    """

    def __init__(self, url: str | None = None, *, prefix: str | None = None) -> None:
        """Connect to Redis and configure key prefix / audit cap.

        Args:
            url: Redis URL; defaults via ``resolve_redis_settings``.
            prefix: Key namespace prefix.

        Raises:
            RuntimeError: Missing ``redis`` package.
        """
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_STATE_STORE=redis requires redis. "
                "Install: pip install 'edim-dde-ai[redis]'"
            ) from exc

        resolved_url, resolved_prefix = resolve_redis_settings(url, prefix=prefix)
        self._prefix = resolved_prefix
        self._audit_max = int(os.environ.get("EDIM_REDIS_AUDIT_MAX", "1000"))
        self._r = redis.Redis.from_url(resolved_url, decode_responses=True)

    @property
    def name(self) -> str:
        """Backend id for health / logs (``redis``)."""
        return "redis"

    def _k(self, *parts: str) -> str:
        return ":".join((self._prefix, *parts))

    def ping(self) -> bool:
        """Redis ``PING``.

        Returns:
            Truthy response from the server.
        """
        return bool(self._r.ping())

    def upsert_agent(self, record: AgentRecord) -> None:
        """Store agent JSON under hash ``{prefix}:agents``.

        Args:
            record: Agent catalog row.
        """
        self._r.hset(self._k("agents"), record.agent_id, json.dumps(record.to_dict()))

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        """Fetch one agent from the agents hash.

        Args:
            agent_id: Agent key.

        Returns:
            ``AgentRecord`` or ``None``.
        """
        raw = self._r.hget(self._k("agents"), agent_id)
        if not raw:
            return None
        return AgentRecord.from_dict(json.loads(raw))

    def list_agents(self) -> list[AgentRecord]:
        """List all agents from the agents hash (sorted by id).

        Returns:
            Sorted agent rows.
        """
        data = self._r.hgetall(self._k("agents"))
        rows = [AgentRecord.from_dict(json.loads(v)) for v in data.values()]
        return sorted(rows, key=lambda r: r.agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        """Delete one agent field from the hash.

        Args:
            agent_id: Agent key.

        Returns:
            ``True`` if a field was removed.
        """
        return bool(self._r.hdel(self._k("agents"), agent_id))

    def upsert_session(self, record: SessionRecord) -> None:
        """Store session JSON under hash ``{prefix}:sessions``.

        Args:
            record: Session document.
        """
        self._r.hset(
            self._k("sessions"), record.session_id, json.dumps(record.to_dict())
        )

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch one session from the sessions hash.

        Args:
            session_id: Session key.

        Returns:
            ``SessionRecord`` or ``None``.
        """
        raw = self._r.hget(self._k("sessions"), session_id)
        if not raw:
            return None
        return SessionRecord.from_dict(json.loads(raw))

    def delete_session(self, session_id: str) -> bool:
        """Delete one session field from the hash.

        Args:
            session_id: Session key.

        Returns:
            ``True`` if a field was removed.
        """
        return bool(self._r.hdel(self._k("sessions"), session_id))

    def append_audit(self, event: AuditEvent) -> None:
        """LPUSH audit JSON and LTRIM to ``EDIM_REDIS_AUDIT_MAX``.

        Args:
            event: Audit event.
        """
        key = self._k("audit")
        self._r.lpush(key, json.dumps(event.to_dict()))
        self._r.ltrim(key, 0, max(0, self._audit_max - 1))

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """Read recent audit list entries (optionally filter by agent).

        Over-fetches when filtering so ``limit`` can still be filled after
        client-side agent filtering.

        Args:
            agent_id: Optional filter.
            limit: Maximum rows to return.

        Returns:
            Up to ``limit`` events (newest first via LPUSH order).
        """
        raw_list = self._r.lrange(self._k("audit"), 0, max(0, limit * 5 - 1))
        events = [AuditEvent.from_dict(json.loads(r)) for r in raw_list]
        if agent_id is not None:
            events = [e for e in events if e.agent_id == agent_id]
        return events[:limit]
