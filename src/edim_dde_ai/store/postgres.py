"""PostgreSQL state store (recommended for local / SDBX / DEV)."""

from __future__ import annotations

import json
import logging
from typing import Any

from edim_dde_ai.store.connection_env import resolve_postgres_dsn
from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS edim_agents (
  agent_id TEXT PRIMARY KEY,
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS edim_sessions (
  session_id TEXT PRIMARY KEY,
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS edim_audit (
  event_id TEXT PRIMARY KEY,
  agent_id TEXT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS edim_audit_agent_idx ON edim_audit (agent_id, created_at DESC);
"""


class PostgresStateStore:
    """Control-plane store backed by PostgreSQL (psycopg v3).

    Install: ``pip install 'edim-dde-ai[postgres]'``

    Env:
      - ``EDIM_DATABASE_URL`` or ``DATABASE_URL``
        e.g. ``postgresql://edim:edim@localhost:5432/edim``
    """

    def __init__(self, dsn: str | None = None) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_STATE_STORE=postgres requires psycopg. "
                "Install: pip install 'edim-dde-ai[postgres]'"
            ) from exc

        self._psycopg = psycopg
        self._dict_row = dict_row
        self._dsn = resolve_postgres_dsn(dsn)
        self.ensure_schema()

    @property
    def name(self) -> str:
        return "postgres"

    def _connect(self):
        return self._psycopg.connect(self._dsn, row_factory=self._dict_row)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)
            conn.commit()

    def ping(self) -> bool:
        with self._connect() as conn:
            conn.execute("SELECT 1")
        return True

    def upsert_agent(self, record: AgentRecord) -> None:
        payload = json.dumps(record.to_dict())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_agents (agent_id, payload, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (agent_id) DO UPDATE
                  SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (record.agent_id, payload),
            )
            conn.commit()

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM edim_agents WHERE agent_id = %s",
                (agent_id,),
            ).fetchone()
        if not row:
            return None
        return AgentRecord.from_dict(_as_dict(row["payload"]))

    def list_agents(self) -> list[AgentRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM edim_agents ORDER BY agent_id"
            ).fetchall()
        return [AgentRecord.from_dict(_as_dict(r["payload"])) for r in rows]

    def delete_agent(self, agent_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM edim_agents WHERE agent_id = %s", (agent_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def upsert_session(self, record: SessionRecord) -> None:
        payload = json.dumps(record.to_dict())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_sessions (session_id, payload, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (session_id) DO UPDATE
                  SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (record.session_id, payload),
            )
            conn.commit()

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM edim_sessions WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return SessionRecord.from_dict(_as_dict(row["payload"]))

    def delete_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM edim_sessions WHERE session_id = %s", (session_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def append_audit(self, event: AuditEvent) -> None:
        payload = json.dumps(event.to_dict())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_audit (event_id, agent_id, payload, created_at)
                VALUES (%s, %s, %s::jsonb, NOW())
                ON CONFLICT (event_id) DO NOTHING
                """,
                (event.event_id, event.agent_id, payload),
            )
            conn.commit()

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        with self._connect() as conn:
            if agent_id is None:
                rows = conn.execute(
                    """
                    SELECT payload FROM edim_audit
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT payload FROM edim_audit
                    WHERE agent_id = %s
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (agent_id, limit),
                ).fetchall()
        return [AuditEvent.from_dict(_as_dict(r["payload"])) for r in rows]


def _as_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    return dict(payload)
