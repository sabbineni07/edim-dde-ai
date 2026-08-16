"""Entity-scoped helpers for chat / Q&A over recommendations + experiences.

Business purpose
----------------
Cross-job learning stays **feature-based**. Operators and future chat still need
"what happened to job X?" — that is an **entity** path over
``RecommendationStore`` plus optional metadata-filtered outcomes search.

How it fits the platform
------------------------
* ``list_recommendations_for_job`` — thin store.list wrapper (system of record)
* ``filter_hits_by_metadata`` — post-filter works on every RetrievalProvider
* ``search_experiences_for_entity`` — ``search_corpus`` + filters + status boost

Public API
----------
* ``list_recommendations_for_job``
* ``filter_hits_by_metadata``
* ``search_experiences_for_entity``
"""

from __future__ import annotations

from typing import Any, Iterable

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.retrieval.models import RetrievalHit


def list_recommendations_for_job(
    job_id: str,
    *,
    agent_id: str | None = None,
    status: str | None = None,
    cluster_id: str | None = None,
    limit: int = 50,
    store: Any | None = None,
) -> list[RecommendationRecord]:
    """List persisted recommendations for one job (exact entity history).

    Args:
        job_id: Job identity to filter on.
        agent_id: Optional agent scope (``spark_rca`` / ``cluster_tuning``).
        status: Optional lifecycle status filter.
        cluster_id: Optional cluster filter (tuning).
        limit: Max rows.
        store: Optional ``RecommendationStore``; defaults to process registry.

    Returns:
        Matching ``RecommendationRecord`` rows from the store.
    """
    if store is None:
        from edim_dde_ai.recommendations import get_recommendation_store

        store = get_recommendation_store()
    kwargs: dict[str, Any] = {
        "job_id": job_id,
        "limit": max(1, int(limit)),
    }
    if agent_id:
        kwargs["agent_id"] = agent_id
    if status:
        kwargs["status"] = status
    if cluster_id:
        kwargs["cluster_id"] = cluster_id
    return list(store.list(**kwargs))


def filter_hits_by_metadata(
    hits: Iterable[RetrievalHit],
    filters: dict[str, Any] | None,
) -> list[RetrievalHit]:
    """Keep hits whose metadata exactly matches every filter value.

    Args:
        hits: Retrieval results.
        filters: ``metadata_key → expected value`` (stringified compare).
            Empty / None → return all hits unchanged.

    Returns:
        Filtered list (order preserved).
    """
    if not filters:
        return list(hits)
    wanted = {str(k): str(v) for k, v in filters.items() if v is not None and str(v) != ""}
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
    job_id: str | None = None,
    job_run_id: str | None = None,
    agent_id: str | None = None,
    status: str | None = None,
    top_k: int = 5,
    search_mode: str = "hybrid",
) -> list[RetrievalHit]:
    """Feature/text search over an outcomes corpus with optional entity filters.

    Args:
        query: Similarity / keyword query (often feature labels).
        corpus: Logical outcomes corpus (e.g. ``spark-rca-outcomes``).
        job_id / job_run_id / agent_id / status: Optional metadata filters.
        top_k: Max hits after filter + boost.
        search_mode: Passed to ``search_corpus``.

    Returns:
        Ranked ``RetrievalHit`` rows (status-boosted when metadata present).
    """
    from edim_dde_ai.retrieval import search_corpus

    filters = {
        k: v
        for k, v in {
            "job_id": job_id,
            "job_run_id": job_run_id,
            "agent_id": agent_id,
            "status": status,
        }.items()
        if v
    }
    return search_corpus(
        query,
        corpus=corpus,
        top_k=top_k,
        search_mode=search_mode,
        filters=filters or None,
        status_boost=True,
    )
