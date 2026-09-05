"""Tests for experience status boost, entity filters, and store backfill."""

from __future__ import annotations

from edim_dde_ai.experiences import (
    BackfillResult,
    apply_status_boost,
    backfill_outcomes_from_store,
    filter_hits_by_metadata,
    list_recommendations,
    maybe_index_experience,
    register_experience_transform,
    search_experiences_for_entity,
)
from edim_dde_ai.experiences.models import ExperienceDocument
from edim_dde_ai.recommendations import (
    MemoryRecommendationStore,
    RecommendationRecord,
    set_recommendation_store,
)
from edim_dde_ai.retrieval import MemoryRetrieval, search_corpus, set_retrieval_provider
from edim_dde_ai.retrieval.models import RetrievalHit


class _ToyTransform:
    agent_id = "toy_agent"
    corpus = "toy-outcomes"

    def transform(self, record: RecommendationRecord) -> ExperienceDocument | None:
        status = str(record.status or "").lower()
        if status == "proposed":
            pass
        return ExperienceDocument(
            doc_id=record.recommendation_id,
            corpus=self.corpus,
            text=(
                f"features for {record.subject('job_id')} status={record.status}"
            ),
            feature_labels=["signal_x"],
            action_signature="action:x",
            metadata={
                "agent_id": self.agent_id,
                "job_id": record.subject("job_id"),
                "status": record.status,
                "action_signature": "action:x",
            },
            source=f"recommendation:{record.recommendation_id}",
        )


def test_apply_status_boost_prefers_applied_over_proposed():
    hits = [
        RetrievalHit(
            id="a",
            text="proposed peer",
            score=1.0,
            metadata={"status": "proposed"},
        ),
        RetrievalHit(
            id="b",
            text="applied peer",
            score=1.0,
            metadata={"status": "applied", "occurrences": 2},
        ),
    ]
    ranked = apply_status_boost(hits)
    assert ranked[0].id == "b"
    assert ranked[0].metadata.get("occurrences") == 2
    assert ranked[0].score > ranked[1].score


def test_search_corpus_status_boost_and_filter():
    store = MemoryRetrieval()
    store.upsert(
        corpus="toy-outcomes",
        doc_id="p1",
        text="memory pressure high proposed",
        metadata={"status": "proposed", "job_id": "job-1", "agent_id": "toy_agent"},
    )
    store.upsert(
        corpus="toy-outcomes",
        doc_id="a1",
        text="memory pressure high applied",
        metadata={"status": "applied", "job_id": "job-2", "agent_id": "toy_agent"},
    )
    store.upsert(
        corpus="toy-outcomes",
        doc_id="other",
        text="memory pressure high other job",
        metadata={"status": "applied", "job_id": "job-9", "agent_id": "toy_agent"},
    )
    set_retrieval_provider(store)

    hits = search_corpus(
        "memory pressure",
        corpus="toy-outcomes",
        top_k=5,
        status_boost=True,
    )
    assert hits[0].id == "a1" or hits[0].metadata.get("status") == "applied"

    filtered = search_corpus(
        "memory pressure",
        corpus="toy-outcomes",
        top_k=5,
        filters={"job_id": "job-1"},
    )
    assert len(filtered) == 1
    assert filtered[0].id == "p1"

    entity = search_experiences_for_entity(
        "memory pressure",
        corpus="toy-outcomes",
        filters={"job_id": "job-2"},
    )
    assert len(entity) == 1
    assert entity[0].id == "a1"


def test_filter_hits_by_metadata_noop_when_empty():
    hits = [RetrievalHit(id="1", text="x", score=1.0, metadata={"job_id": "j"})]
    assert filter_hits_by_metadata(hits, None) == hits
    assert filter_hits_by_metadata(hits, {}) == hits


def test_list_recommendations_and_backfill(monkeypatch):
    rec_store = MemoryRecommendationStore()
    set_recommendation_store(rec_store)
    register_experience_transform(_ToyTransform())

    retrieval = MemoryRetrieval()
    set_retrieval_provider(retrieval)

    applied = RecommendationRecord(
        recommendation_id="r-applied",
        agent_id="toy_agent",
        subjects={"job_id": "job-42"},
        status="applied",
        response={"ok": True},
    )
    proposed = RecommendationRecord(
        recommendation_id="r-proposed",
        agent_id="toy_agent",
        subjects={"job_id": "job-42"},
        status="proposed",
        response={"ok": True},
    )
    other = RecommendationRecord(
        recommendation_id="r-other",
        agent_id="toy_agent",
        subjects={"job_id": "job-99"},
        status="applied",
        response={"ok": True},
    )
    store = rec_store
    store.save(applied)
    store.save(proposed)
    store.save(other)

    rows = list_recommendations(
        agent_id="toy_agent", subjects={"job_id": "job-42"}
    )
    assert {r.recommendation_id for r in rows} == {"r-applied", "r-proposed"}

    set_retrieval_provider(MemoryRetrieval())
    dry = backfill_outcomes_from_store(agent_id="toy_agent", dry_run=True, limit=50)
    assert isinstance(dry, BackfillResult)
    assert dry.dry_run is True
    assert dry.indexed >= 2

    live = backfill_outcomes_from_store(agent_id="toy_agent", dry_run=False, limit=50)
    assert live.indexed >= 2
    assert live.failed == 0
    hits = search_corpus("job-42", corpus="toy-outcomes", top_k=5)
    assert hits
