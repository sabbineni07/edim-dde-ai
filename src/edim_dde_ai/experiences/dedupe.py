"""Post-search de-duplication for retrieval hits (id + content/action).

Business purpose
----------------
Similarity search can return near-duplicate outcomes (same recommendation id
across shards, or different jobs with the same recommended action). Agents
want a short, non-redundant prompt list **without** hiding that a pattern is
common.

How it fits the platform
------------------------
Called after ``search_corpus`` in domain historical-context helpers. Survivors
carry ``metadata['occurrences']`` and optional ``also_job_ids`` so prompts can
say "seen N times across jobs".

Public API
----------
* ``content_hash`` — stable short hash of normalized body text
* ``action_signature_from_hit`` — metadata signature or content hash fallback
* ``dedupe_retrieval_hits`` — collapse by id, then optionally by action
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from edim_dde_ai.retrieval.models import RetrievalHit

_WS = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Collapse whitespace and lowercase for stable hashing."""
    return _WS.sub(" ", (text or "").strip().lower())


def content_hash(text: str) -> str:
    """Stable short hash of normalized body text.

    Args:
        text: Hit body or free-form action text.

    Returns:
        First 16 hex chars of SHA-256 over normalized UTF-8 bytes.
    """
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()[:16]


def action_signature_from_hit(hit: RetrievalHit) -> str:
    """Prefer metadata.action_signature; else hash of body text.

    Args:
        hit: One retrieval result.

    Returns:
        Lowercased action signature string used as the second-pass dedupe key.
    """
    meta = hit.metadata or {}
    sig = str(meta.get("action_signature") or "").strip()
    if sig:
        return sig.lower()
    return content_hash(hit.text)


def dedupe_retrieval_hits(
    hits: Iterable[RetrievalHit],
    *,
    by_action: bool = True,
) -> list[RetrievalHit]:
    """Keep highest-score hit per ``id``, then optionally per action signature.

    Collapsed duplicates are **counted, not discarded**: the survivor carries
    ``metadata['occurrences']`` (how many rows shared that action) and
    ``metadata['also_job_ids']`` so prompts can say "seen N times across jobs"
    instead of silently hiding that a pattern is common.

    Order is preserved among survivors (input should already be score-sorted).

    Args:
        hits: Score-ordered retrieval results (may contain duplicates).
        by_action: When ``True`` (default), also collapse by action signature
            after the per-id pass. When ``False``, only collapse by ``id``.

    Returns:
        Deduplicated list of ``RetrievalHit`` with occurrence metadata.

    Example:
        >>> dedupe_retrieval_hits(hits, by_action=True)  # doctest: +SKIP
    """
    by_id: dict[str, RetrievalHit] = {}
    order: list[str] = []
    for hit in hits:
        key = str(hit.id or "")
        if not key:
            key = f"_anon_{id(hit)}"
        if key not in by_id:
            by_id[key] = hit
            order.append(key)
        elif float(hit.score) > float(by_id[key].score):
            by_id[key] = hit

    unique_ids = [by_id[k] for k in order]
    if not by_action:
        return unique_ids

    survivors: dict[str, RetrievalHit] = {}
    sig_order: list[str] = []
    extra_jobs: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for hit in unique_ids:
        sig = action_signature_from_hit(hit)
        counts[sig] = counts.get(sig, 0) + 1
        if sig not in survivors:
            survivors[sig] = hit
            sig_order.append(sig)
            extra_jobs[sig] = []
            continue
        job_id = str((hit.metadata or {}).get("job_id") or "").strip()
        if job_id and job_id not in extra_jobs[sig]:
            extra_jobs[sig].append(job_id)

    out: list[RetrievalHit] = []
    for sig in sig_order:
        hit = survivors[sig]
        meta = dict(hit.metadata or {})
        meta["occurrences"] = counts[sig]
        if extra_jobs[sig]:
            meta["also_job_ids"] = extra_jobs[sig]
        out.append(
            RetrievalHit(
                id=hit.id,
                text=hit.text,
                score=hit.score,
                metadata=meta,
                source=hit.source,
            )
        )
    return out
