"""Registry of ExperienceTransform strategies + store wrapper for auto-index."""

from __future__ import annotations

import logging
from typing import Any

from edim_dde_ai.experiences.protocols import ExperienceTransform
from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.protocols import RecommendationStore

logger = logging.getLogger(__name__)

_TRANSFORMS: dict[str, ExperienceTransform] = {}


def register_experience_transform(transform: ExperienceTransform) -> None:
    """Register (or replace) the transform for ``transform.agent_id``."""
    agent_id = str(transform.agent_id).strip()
    if not agent_id:
        raise ValueError("ExperienceTransform.agent_id must be non-empty")
    _TRANSFORMS[agent_id] = transform
    logger.info(
        "experience transform registered agent_id=%s corpus=%s",
        agent_id,
        getattr(transform, "corpus", "?"),
    )


def get_experience_transform(agent_id: str) -> ExperienceTransform | None:
    return _TRANSFORMS.get(str(agent_id).strip())


def list_experience_transforms() -> list[str]:
    return sorted(_TRANSFORMS)


def clear_experience_transforms() -> None:
    _TRANSFORMS.clear()


class ExperienceIndexingStore:
    """Decorator / Proxy: RecommendationStore writes also update the experience index.

    Keeps indexing orthogonal to backends (memory/postgres/cosmos/redis/none).
    Upsert is idempotent by ``recommendation_id``; failures never fail the write.
    """

    def __init__(self, inner: RecommendationStore) -> None:
        self._inner = inner

    @property
    def inner(self) -> RecommendationStore:
        return self._inner

    @property
    def name(self) -> str:
        return getattr(self._inner, "name", type(self._inner).__name__)

    def ping(self) -> bool:
        return bool(self._inner.ping())

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        out = self._inner.save(record)
        self._index(out)
        return out

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        return self._inner.get(recommendation_id)

    def list(self, **kwargs: Any) -> list[RecommendationRecord]:
        return self._inner.list(**kwargs)

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        out = self._inner.update_status(recommendation_id, status)
        if out is not None:
            self._index(out)
        return out

    @staticmethod
    def _index(record: RecommendationRecord) -> None:
        try:
            from edim_dde_ai.experiences.indexing import maybe_index_experience

            maybe_index_experience(record)
        except Exception as exc:  # noqa: BLE001
            logger.warning("experience index hook failed: %s", exc)


def wrap_recommendation_store(store: RecommendationStore) -> RecommendationStore:
    """Wrap unless already wrapped or backend is ``none``."""
    if isinstance(store, ExperienceIndexingStore):
        return store
    if getattr(store, "name", "") == "none":
        return store
    return ExperienceIndexingStore(store)
