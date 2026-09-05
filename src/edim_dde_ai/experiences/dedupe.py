"""Post-search de-duplication for retrieval hits (id + content/action)."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, Sequence

from edim_dde_ai.retrieval.models import RetrievalHit

_WS = re.compile(r"\s+")

_DEFAULT_ENTITY_ID_KEYS: tuple[str, ...] = (
    "entity_id",
    "subject_id",
    "job_id",
    "ticket_id",
)


def _normalize_text(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def content_hash(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()[:16]


def action_signature_from_hit(hit: RetrievalHit) -> str:
    meta = hit.metadata or {}
    sig = str(meta.get("action_signature") or "").strip()
    if sig:
        return sig.lower()
    return content_hash(hit.text)


def _entity_id_from_meta(
    meta: dict, entity_id_keys: Sequence[str]
) -> str | None:
    for key in entity_id_keys:
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return None


def dedupe_retrieval_hits(
    hits: Iterable[RetrievalHit],
    *,
    by_action: bool = True,
    entity_id_keys: Sequence[str] | None = None,
) -> list[RetrievalHit]:
    """Keep highest-score hit per ``id``, then optionally per action signature.

    Survivors carry ``metadata['occurrences']`` and ``metadata['also_entity_ids']``.
    """
    keys = tuple(entity_id_keys) if entity_id_keys is not None else _DEFAULT_ENTITY_ID_KEYS

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
    extra_entities: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for hit in unique_ids:
        sig = action_signature_from_hit(hit)
        counts[sig] = counts.get(sig, 0) + 1
        if sig not in survivors:
            survivors[sig] = hit
            sig_order.append(sig)
            extra_entities[sig] = []
            continue
        entity_id = _entity_id_from_meta(hit.metadata or {}, keys)
        if entity_id and entity_id not in extra_entities[sig]:
            extra_entities[sig].append(entity_id)

    out: list[RetrievalHit] = []
    for sig in sig_order:
        hit = survivors[sig]
        meta = dict(hit.metadata or {})
        meta["occurrences"] = counts[sig]
        if extra_entities[sig]:
            meta["also_entity_ids"] = extra_entities[sig]
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
