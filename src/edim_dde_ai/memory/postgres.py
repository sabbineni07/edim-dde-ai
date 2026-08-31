"""PostgreSQL conversation store, including Lakebase-compatible deployments."""

from __future__ import annotations

import json

from edim_dde_ai.memory.models import ConversationMessage, ConversationSummary
from edim_dde_ai.store.connection_env import resolve_postgres_dsn

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS edim_conversation_messages (
  message_id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS edim_conversation_messages_idx
  ON edim_conversation_messages (conversation_id, created_at, message_id);
CREATE TABLE IF NOT EXISTS edim_conversation_summaries (
  conversation_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  content TEXT NOT NULL,
  covered_message_id TEXT NULL,
  updated_at TEXT NOT NULL
);
"""


class PostgresConversationStore:
    """Durable conversation store backed by PostgreSQL JSONB metadata."""

    def __init__(self, dsn: str | None = None, *, name: str = "postgres") -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Conversation store requires psycopg. "
                "Install: pip install 'edim-dde-ai[postgres]'"
            ) from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._dsn = resolve_postgres_dsn(dsn)
        self._name = name
        self.ensure_schema()

    @property
    def name(self) -> str:
        return self._name

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

    def append_message(self, message: ConversationMessage) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_conversation_messages
                  (message_id, conversation_id, agent_id, role, content,
                   created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (message_id) DO NOTHING
                """,
                (
                    message.message_id,
                    message.conversation_id,
                    message.agent_id,
                    message.role,
                    message.content,
                    message.created_at,
                    json.dumps(message.metadata),
                ),
            )
            conn.commit()

    def list_messages(
        self,
        conversation_id: str,
        *,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationMessage]:
        if limit <= 0:
            return []
        clause = "conversation_id = %s"
        params: list[object] = [conversation_id]
        if agent_id is not None:
            clause += " AND agent_id = %s"
            params.append(agent_id)
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT message_id, conversation_id, agent_id, role, content,
                       created_at, metadata
                FROM edim_conversation_messages
                WHERE {clause}
                ORDER BY created_at DESC, message_id DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        return [
            ConversationMessage.from_dict(dict(row))
            for row in reversed(rows)
        ]

    def get_summary(
        self, conversation_id: str, *, agent_id: str | None = None
    ) -> ConversationSummary | None:
        clause = "conversation_id = %s"
        params: list[object] = [conversation_id]
        if agent_id is not None:
            clause += " AND agent_id = %s"
            params.append(agent_id)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT conversation_id, agent_id, content,
                       covered_message_id, updated_at
                FROM edim_conversation_summaries
                WHERE {clause}
                """,
                params,
            ).fetchone()
        return ConversationSummary.from_dict(dict(row)) if row else None

    def upsert_summary(self, summary: ConversationSummary) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_conversation_summaries
                  (conversation_id, agent_id, content, covered_message_id, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE SET
                  agent_id = EXCLUDED.agent_id,
                  content = EXCLUDED.content,
                  covered_message_id = EXCLUDED.covered_message_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    summary.conversation_id,
                    summary.agent_id,
                    summary.content,
                    summary.covered_message_id,
                    summary.updated_at,
                ),
            )
            conn.commit()

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            messages = conn.execute(
                "DELETE FROM edim_conversation_messages WHERE conversation_id = %s",
                (conversation_id,),
            )
            summary = conn.execute(
                "DELETE FROM edim_conversation_summaries WHERE conversation_id = %s",
                (conversation_id,),
            )
            conn.commit()
        return bool(messages.rowcount or summary.rowcount)
