"""Post-search de-duplication for retrieval hits (id + content/action)."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from edim_dde_ai.retrieval.models import RetrievalHit

_WS = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def content_hash(text: str) -> str:
    """Stable short hash of normalized body text."""
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()[:16]


def action_signature_from_hit(hit: RetrievalHit) -> str:
    """Prefer metadata.action_signature; else hash of body text."""
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
