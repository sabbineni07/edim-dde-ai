"""Post-search status boost for experience / outcomes hits.

Business purpose
----------------
Similarity scores alone do not know whether an operator accepted or applied a
past recommendation. After the provider returns hits (and after de-dupe), we
nudge ``applied`` / ``accepted`` slightly above ``proposed`` so prompts lean on
reviewed outcomes when scores are close.

How it fits the platform
------------------------
Wired from ``search_corpus(..., status_boost=True)``. Safe no-op when hits lack
``metadata.status`` (runbooks / guidance). Does **not** change Azure/FAISS
scoring or de-dupe survivor selection.

Public API
----------
* ``DEFAULT_STATUS_BOOST`` — additive score deltas by lifecycle status
* ``status_boost_for`` — lookup one status
* ``apply_status_boost`` — bump scores and optionally re-sort
"""

from __future__ import annotations

from typing import Iterable

from edim_dde_ai.retrieval.models import RetrievalHit

DEFAULT_STATUS_BOOST: dict[str, float] = {
    "applied": 0.08,
    "accepted": 0.05,
    "proposed": 0.0,
}


def status_boost_for(
    status: str | None, *, boosts: dict[str, float] | None = None
) -> float:
    """Return the additive score boost for a lifecycle status.

    Args:
        status: Recommendation status (case-insensitive).
        boosts: Optional override map; defaults to ``DEFAULT_STATUS_BOOST``.

    Returns:
        Non-negative float boost (0.0 when status unknown / empty).
    """
    table = boosts if boosts is not None else DEFAULT_STATUS_BOOST
    key = str(status or "").strip().lower()
    if not key:
        return 0.0
    return float(table.get(key, 0.0))


def apply_status_boost(
    hits: Iterable[RetrievalHit],
    *,
    boosts: dict[str, float] | None = None,
    resort: bool = True,
) -> list[RetrievalHit]:
    """Add status boost to each hit score; optionally re-sort descending.

    Preserves ``metadata`` (including ``occurrences`` / ``also_job_ids`` from
    de-dupe). Hits without ``metadata.status`` are unchanged.

    Args:
        hits: Provider (or de-duped) retrieval results.
        boosts: Optional status → delta map.
        resort: When true (default), sort by boosted score descending.

    Returns:
        New list of ``RetrievalHit`` with adjusted ``score`` values.

    Example:
        >>> apply_status_boost(hits)  # doctest: +SKIP
    """
    out: list[RetrievalHit] = []
    for hit in hits:
        meta = dict(hit.metadata or {})
        delta = status_boost_for(meta.get("status"), boosts=boosts)
        if delta:
            meta["status_boost"] = delta
        out.append(
            RetrievalHit(
                id=hit.id,
                text=hit.text,
                score=float(hit.score or 0.0) + delta,
                metadata=meta,
                source=hit.source,
            )
        )
    if resort:
        out.sort(key=lambda h: float(h.score or 0.0), reverse=True)
    return out
