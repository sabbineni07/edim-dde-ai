"""PostgreSQL recommendation history store."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.support import (
    RecommendationStatusMixin,
    payload_as_dict,
)
from edim_dde_ai.store.connection_env import resolve_postgres_dsn

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS edim_recommendations (
  recommendation_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  status TEXT NOT NULL,
  subjects JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE edim_recommendations ADD COLUMN IF NOT EXISTS subjects JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE edim_recommendations DROP COLUMN IF EXISTS job_id;
ALTER TABLE edim_recommendations DROP COLUMN IF EXISTS cluster_id;
CREATE INDEX IF NOT EXISTS edim_recommendations_agent_idx
  ON edim_recommendations (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS edim_recommendations_status_idx
  ON edim_recommendations (status, created_at DESC);
CREATE INDEX IF NOT EXISTS edim_recommendations_subjects_gin
  ON edim_recommendations USING GIN (subjects);
"""


class PostgresRecommendationStore(RecommendationStatusMixin):
    """Recommendation history in PostgreSQL (same DSN as StateStore by default)."""

    def __init__(self, dsn: str | None = None) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RECOMMENDATION_STORE=postgres requires psycopg. "
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

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        payload = json.dumps(record.to_dict())
        subjects = json.dumps(record.subjects or {})
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_recommendations (
                  recommendation_id, agent_id, status, subjects, payload,
                  created_at, updated_at
                )
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, NOW(), NOW())
                ON CONFLICT (recommendation_id) DO UPDATE
                  SET agent_id = EXCLUDED.agent_id,
                      status = EXCLUDED.status,
                      subjects = EXCLUDED.subjects,
                      payload = EXCLUDED.payload,
                      updated_at = NOW()
                """,
                (
                    record.recommendation_id,
                    record.agent_id,
                    record.status,
                    subjects,
                    payload,
                ),
            )
            conn.commit()
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM edim_recommendations WHERE recommendation_id = %s",
                (recommendation_id,),
            ).fetchone()
        if not row:
            return None
        return RecommendationRecord.from_dict(payload_as_dict(row["payload"]))

    def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        subjects: Mapping[str, Any] | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if agent_id is not None:
            clauses.append("agent_id = %s")
            params.append(agent_id)
        clean_subjects = {
            str(k): v
            for k, v in dict(subjects or {}).items()
            if v is not None and str(v) != ""
        }
        if clean_subjects:
            clauses.append("subjects @> %s::jsonb")
            params.append(json.dumps(clean_subjects))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, limit))
        sql = f"""
            SELECT payload FROM edim_recommendations
            {where}
            ORDER BY created_at DESC
            LIMIT %s
        """
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            RecommendationRecord.from_dict(payload_as_dict(r["payload"])) for r in rows
        ]
