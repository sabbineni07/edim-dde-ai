"""Entity-scoped helpers for recommendations + experiences (agent-agnostic)."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.retrieval.models import RetrievalHit


def list_recommendations(
    *,
    agent_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    store: Any | None = None,
    subjects: Mapping[str, Any] | None = None,
) -> list[RecommendationRecord]:
    """List persisted recommendations with optional subject filters."""
    if store is None:
        from edim_dde_ai.recommendations import get_recommendation_store

        store = get_recommendation_store()
    return list(
        store.list(
            agent_id=agent_id,
            status=status,
            subjects=dict(subjects) if subjects else None,
            limit=max(1, int(limit)),
        )
    )


def filter_hits_by_metadata(
    hits: Iterable[RetrievalHit],
    filters: dict[str, Any] | None,
) -> list[RetrievalHit]:
    """Keep hits whose metadata exactly matches every filter value."""
    if not filters:
        return list(hits)
    wanted = {
        str(k): str(v) for k, v in filters.items() if v is not None and str(v) != ""
    }
    if not wanted:
        return list(hits)
    out: list[RetrievalHit] = []
    for hit in hits:
        meta = hit.metadata or {}
        if all(str(meta.get(k, "")) == v for k, v in wanted.items()):
            out.append(hit)
    return out


def search_experiences_for_entity(
    query: str,
    *,
    corpus: str,
    filters: Mapping[str, Any] | None = None,
    top_k: int = 5,
    search_mode: str = "hybrid",
) -> list[RetrievalHit]:
    """Feature/text search over an outcomes corpus with optional metadata filters."""
    from edim_dde_ai.retrieval import search_corpus

    clean = {
        str(k): v
        for k, v in dict(filters or {}).items()
        if v is not None and str(v) != ""
    }
    return search_corpus(
        query,
        corpus=corpus,
        top_k=top_k,
        search_mode=search_mode,
        filters=clean or None,
        status_boost=True,
    )
