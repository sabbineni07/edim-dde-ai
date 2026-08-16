"""ExperienceTransform registry and RecommendationStore auto-index wrapper.

Business purpose
----------------
Domain packs register one ``ExperienceTransform`` per ``agent_id``. Hosts
install a ``RecommendationStore``; this module wraps it so ``save`` /
``update_status`` also refresh the experience retrieval corpus.

How it fits the platform
------------------------
* Transform map is process-wide (same pattern as web-search / recommendation
  registries).
* ``set_recommendation_store`` calls ``wrap_recommendation_store`` so production
  backends get indexing without each backend knowing about experiences.
* Index failures are logged and swallowed — product history writes must not fail.

Public API
----------
* ``register_experience_transform`` / ``get_experience_transform`` /
  ``list_experience_transforms`` / ``clear_experience_transforms``
* ``ExperienceIndexingStore`` — Decorator / Proxy over ``RecommendationStore``
* ``wrap_recommendation_store`` — idempotent wrap (skips ``none`` backend)
"""

from __future__ import annotations

import logging
from typing import Any

from edim_dde_ai.experiences.protocols import ExperienceTransform
from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.protocols import RecommendationStore

logger = logging.getLogger(__name__)

_TRANSFORMS: dict[str, ExperienceTransform] = {}


def register_experience_transform(transform: ExperienceTransform) -> None:
    """Register (or replace) the transform for ``transform.agent_id``.

    Args:
        transform: Domain strategy implementing ``ExperienceTransform``.

    Raises:
        ValueError: Empty ``agent_id``.
    """
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
    """Look up the registered transform for ``agent_id``.

    Args:
        agent_id: Agent id on the recommendation row.

    Returns:
        The transform, or ``None`` if none registered (indexing no-ops).
    """
    return _TRANSFORMS.get(str(agent_id).strip())


def list_experience_transforms() -> list[str]:
    """Return sorted registered ``agent_id`` keys (health / diagnostics)."""
    return sorted(_TRANSFORMS)


def clear_experience_transforms() -> None:
    """Remove all transforms (tests)."""
    _TRANSFORMS.clear()


class ExperienceIndexingStore:
    """Decorator / Proxy: RecommendationStore writes also update the experience index.

    Keeps indexing orthogonal to backends (memory/postgres/cosmos/redis/none).
    Upsert is idempotent by ``recommendation_id``; failures never fail the write.

    Args:
        inner: Concrete ``RecommendationStore`` to wrap.
    """

    def __init__(self, inner: RecommendationStore) -> None:
        self._inner = inner

    @property
    def inner(self) -> RecommendationStore:
        """Underlying store (unwrap for tests / admin)."""
        return self._inner

    @property
    def name(self) -> str:
        """Delegate backend name for health checks."""
        return getattr(self._inner, "name", type(self._inner).__name__)

    def ping(self) -> bool:
        """Delegate reachability check to the inner store."""
        return bool(self._inner.ping())

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        """Persist then best-effort index the returned row.

        Args:
            record: Recommendation to insert/replace.

        Returns:
            The record returned by the inner ``save``.
        """
        out = self._inner.save(record)
        self._index(out)
        return out

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        """Fetch by id (no index side effect)."""
        return self._inner.get(recommendation_id)

    def list(self, **kwargs: Any) -> list[RecommendationRecord]:
        """List with filters (no index side effect)."""
        return self._inner.list(**kwargs)

    def update_status(
        self, recommendation_id: str, status: str
    ) -> RecommendationRecord | None:
        """Transition status then re-index (or delete) when the row exists.

        Args:
            recommendation_id: Target row id.
            status: New lifecycle status.

        Returns:
            Updated record, or ``None`` if missing.
        """
        out = self._inner.update_status(recommendation_id, status)
        if out is not None:
            self._index(out)
        return out

    @staticmethod
    def _index(record: RecommendationRecord) -> None:
        """Best-effort experience upsert/delete; never raises to callers."""
        try:
            from edim_dde_ai.experiences.indexing import maybe_index_experience

            maybe_index_experience(record)
        except Exception as exc:  # noqa: BLE001
            logger.warning("experience index hook failed: %s", exc)


def wrap_recommendation_store(store: RecommendationStore) -> RecommendationStore:
    """Wrap unless already wrapped or backend is ``none``.

    Args:
        store: Store from the factory / test harness.

    Returns:
        ``ExperienceIndexingStore`` wrapper, or ``store`` unchanged when
        already wrapped or when ``name == "none"`` (persistence disabled).

    Example:
        ``set_recommendation_store`` always routes through this helper so
        hosts do not forget to enable indexing.
    """
    if isinstance(store, ExperienceIndexingStore):
        return store
    if getattr(store, "name", "") == "none":
        return store
    return ExperienceIndexingStore(store)
