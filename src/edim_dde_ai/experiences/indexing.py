"""Index / unindex experience documents via the active RetrievalProvider."""

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
    return _INDEX_STATUSES


def maybe_index_experience(record: RecommendationRecord) -> bool:
    """Upsert or delete the experience doc for ``record``. Never raises.

    Returns True when an upsert or delete was attempted successfully.
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
    """Write one experience document into the retrieval backend."""
    try:
        if provider is None:
            from edim_dde_ai.retrieval import provider_for_corpus

            provider = provider_for_corpus(doc.corpus)
        if getattr(provider, "name", "") == "none":
            return False

        meta = dict(doc.metadata or {})
        meta.setdefault("situation_labels", list(doc.situation_labels))
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
