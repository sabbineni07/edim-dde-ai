"""Index / unindex experience documents via the active RetrievalProvider.

Business purpose
----------------
After a recommendation is saved or its status changes, this module decides
whether the derived experience card should be **upserted**, **deleted**, or
left alone — based on lifecycle status and the registered transform.

How it fits the platform
------------------------
* Called from ``ExperienceIndexingStore`` (and optionally directly in tests).
* Resolves RetrievalProvider via ``provider_for_corpus`` / default registry.
* Fail-open: any error is logged; callers always get a bool, never a raise.

Status policy
-------------
* Index: ``proposed``, ``accepted``, ``applied``
* Remove: ``rejected``, ``superseded``
* Other statuses: no-op

Public API
----------
* ``indexable_statuses`` — frozenset of statuses that upsert
* ``maybe_index_experience`` — status-gated upsert or delete
* ``upsert_experience_document`` — write one card into retrieval
"""

from __future__ import annotations

import logging
from typing import Any

from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.experiences.registry import get_experience_transform
from edim_dde_ai.recommendations.models import RecommendationRecord

logger = logging.getLogger(__name__)

# Index proposed (cold-start) + accepted/applied (what we did / plan to do).
# Rejected / superseded are removed so the corpus stays outcome-useful.
_INDEX_STATUSES = frozenset({"proposed", "accepted", "applied"})
_REMOVE_STATUSES = frozenset({"rejected", "superseded"})


def indexable_statuses() -> frozenset[str]:
    """Return statuses that trigger an experience upsert.

    Returns:
        Frozen set: ``proposed``, ``accepted``, ``applied``.
    """
    return _INDEX_STATUSES


def maybe_index_experience(record: RecommendationRecord) -> bool:
    """Upsert or delete the experience doc for ``record``. Never raises.

    Looks up the transform for ``record.agent_id``, resolves a non-``none``
    retrieval provider for that corpus, then either deletes (rejected /
    superseded) or transforms + upserts (indexable statuses).

    Args:
        record: Persisted recommendation lifecycle row.

    Returns:
        ``True`` when an upsert or delete was attempted successfully;
        ``False`` when skipped (no transform, none provider, empty doc,
        non-indexable status) or on failure.
    """
    try:
        status = str(record.status or "").strip().lower()
        transform = get_experience_transform(record.agent_id)
        if transform is None:
            return False

        from edim_dde_ai.retrieval import get_retrieval_provider, provider_for_corpus

        provider = provider_for_corpus(transform.corpus)
        if getattr(provider, "name", "") == "none":
            # Still try default provider in case corpus has no override
            provider = get_retrieval_provider()
        if getattr(provider, "name", "") == "none":
            return False

        doc_id = str(record.recommendation_id)
        if status in _REMOVE_STATUSES:
            try:
                provider.delete(corpus=transform.corpus, doc_id=doc_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "experience delete failed corpus=%s id=%s: %s",
                    transform.corpus,
                    doc_id,
                    exc,
                )
                return False
            return True

        if status not in _INDEX_STATUSES:
            return False

        doc = transform.transform(record)
        if doc is None or not (doc.text or "").strip():
            return False
        return upsert_experience_document(doc, provider=provider)
    except Exception as exc:  # noqa: BLE001
        logger.warning("maybe_index_experience failed: %s", exc)
        return False


def upsert_experience_document(
    doc: ExperienceDocument, *, provider: Any | None = None
) -> bool:
    """Write one experience document into the retrieval backend.

    Copies ``feature_labels`` and ``action_signature`` into metadata when
    absent so search hits carry dedupe / display fields.

    Args:
        doc: Card to upsert (``doc_id`` + ``corpus`` + ``text`` required).
        provider: Optional RetrievalProvider; defaults to corpus routing.

    Returns:
        ``True`` on successful upsert; ``False`` if provider is ``none`` or
        the write failed (logged).
    """
    try:
        if provider is None:
            from edim_dde_ai.retrieval import provider_for_corpus

            provider = provider_for_corpus(doc.corpus)
        if getattr(provider, "name", "") == "none":
            return False

        meta = dict(doc.metadata or {})
        meta.setdefault("feature_labels", list(doc.feature_labels))
        meta.setdefault("action_signature", doc.action_signature)
        provider.upsert(
            corpus=doc.corpus,
            doc_id=doc.doc_id,
            text=doc.text,
            metadata=meta,
            source=doc.source,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "experience upsert failed corpus=%s id=%s: %s",
            doc.corpus,
            doc.doc_id,
            exc,
        )
        return False
