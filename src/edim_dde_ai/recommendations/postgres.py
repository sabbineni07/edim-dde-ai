"""PostgreSQL recommendation history store."""

from __future__ import annotations

import json
import logging
from typing import Any

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
  job_id TEXT NULL,
  cluster_id TEXT NULL,
  status TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS edim_recommendations_job_idx
  ON edim_recommendations (job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS edim_recommendations_status_idx
  ON edim_recommendations (status, created_at DESC);
"""


class PostgresRecommendationStore(RecommendationStatusMixin):
    """Recommendation history in PostgreSQL (same DSN as StateStore by default).

    Install: ``pip install 'edim-dde-ai[postgres]'``

    Env: ``EDIM_DATABASE_URL`` or ``DATABASE_URL``
    """

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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edim_recommendations (
                  recommendation_id, agent_id, job_id, cluster_id, status, payload,
                  created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
                ON CONFLICT (recommendation_id) DO UPDATE
                  SET agent_id = EXCLUDED.agent_id,
                      job_id = EXCLUDED.job_id,
                      cluster_id = EXCLUDED.cluster_id,
                      status = EXCLUDED.status,
                      payload = EXCLUDED.payload,
                      updated_at = NOW()
                """,
                (
                    record.recommendation_id,
                    record.agent_id,
                    record.job_id,
                    record.cluster_id,
                    record.status,
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
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if job_id is not None:
            clauses.append("job_id = %s")
            params.append(job_id)
        if cluster_id is not None:
            clauses.append("cluster_id = %s")
            params.append(cluster_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if agent_id is not None:
            clauses.append("agent_id = %s")
            params.append(agent_id)
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
