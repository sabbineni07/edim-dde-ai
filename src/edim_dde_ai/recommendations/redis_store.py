"""Redis recommendation history store."""

from __future__ import annotations

import json
import logging

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.support import (
    RecommendationStatusMixin,
    created_at_score,
    filter_recommendation_rows,
)
from edim_dde_ai.store.connection_env import resolve_redis_settings

logger = logging.getLogger(__name__)


class RedisRecommendationStore(RecommendationStatusMixin):
    """Recommendation history in Redis (hash + sorted set by created_at).

    Install: ``pip install 'edim-dde-ai[redis]'``

    Env: ``EDIM_REDIS_URL``, ``EDIM_REDIS_PREFIX`` (same as StateStore).
    """

    def __init__(self, url: str | None = None, *, prefix: str | None = None) -> None:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RECOMMENDATION_STORE=redis requires redis. "
                "Install: pip install 'edim-dde-ai[redis]'"
            ) from exc

        resolved_url, resolved_prefix = resolve_redis_settings(url, prefix=prefix)
        self._prefix = resolved_prefix
        self._r = redis.Redis.from_url(resolved_url, decode_responses=True)

    @property
    def name(self) -> str:
        return "redis"

    def _k(self, *parts: str) -> str:
        return ":".join((self._prefix, "recommendations", *parts))

    def ping(self) -> bool:
        return bool(self._r.ping())

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        self._r.hset(
            self._k("by_id"),
            record.recommendation_id,
            json.dumps(record.to_dict()),
        )
        self._r.zadd(
            self._k("index"),
            {record.recommendation_id: created_at_score(record.created_at)},
        )
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        raw = self._r.hget(self._k("by_id"), recommendation_id)
        if not raw:
            return None
        return RecommendationRecord.from_dict(json.loads(raw))

    def list(
        self,
        *,
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        # Prefer ZSET order when no filters; otherwise scan + filter.
        if job_id is None and cluster_id is None and status is None and agent_id is None:
            ids = self._r.zrevrange(self._k("index"), 0, max(0, limit - 1))
            rows: list[RecommendationRecord] = []
            for rid in ids:
                raw = self._r.hget(self._k("by_id"), rid)
                if raw:
                    rows.append(RecommendationRecord.from_dict(json.loads(raw)))
            return rows

        ids = self._r.hkeys(self._k("by_id"))
        rows = []
        for rid in ids:
            raw = self._r.hget(self._k("by_id"), rid)
            if raw:
                rows.append(RecommendationRecord.from_dict(json.loads(raw)))
        return filter_recommendation_rows(
            rows,
            job_id=job_id,
            cluster_id=cluster_id,
            status=status,
            agent_id=agent_id,
            limit=limit,
        )
