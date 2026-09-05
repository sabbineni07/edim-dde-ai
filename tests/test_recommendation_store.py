"""Recommendation store tests (memory + registry)."""

from __future__ import annotations

import pytest

from edim_dde_ai.recommendations import (
    MemoryRecommendationStore,
    RecommendationRecord,
    clear_recommendation_store,
    configure_recommendation_store_from_env,
    create_recommendation_store,
    get_recommendation_store,
    new_recommendation_id,
    resolve_recommendation_store_name,
    set_recommendation_store,
)
from edim_dde_ai.recommendations.support import (
    created_at_score,
    filter_recommendation_rows,
)


def test_created_at_score_iso():
    assert created_at_score("2026-08-14T12:00:00+00:00") > 0
    assert created_at_score("not-a-date") == 0.0


def test_filter_recommendation_rows():
    a = RecommendationRecord(
        recommendation_id="a",
        agent_id="demo",
        subjects={"job_id": "j-1"},
        status="proposed",
        created_at="2026-01-02T00:00:00+00:00",
    )
    b = RecommendationRecord(
        recommendation_id="b",
        agent_id="demo",
        subjects={"job_id": "j-2"},
        status="accepted",
        created_at="2026-01-03T00:00:00+00:00",
    )
    out = filter_recommendation_rows([a, b], subjects={"job_id": "j-1"})
    assert [r.recommendation_id for r in out] == ["a"]


def test_resolve_inherits_state_store(monkeypatch):
    monkeypatch.delenv("EDIM_RECOMMENDATION_STORE", raising=False)
    monkeypatch.setenv("EDIM_STATE_STORE", "memory")
    assert resolve_recommendation_store_name(None) == "memory"
    monkeypatch.setenv("EDIM_RECOMMENDATION_STORE", "none")
    assert resolve_recommendation_store_name(None) == "none"
    monkeypatch.setenv("EDIM_RECOMMENDATION_STORE", "postgres")
    assert resolve_recommendation_store_name(None) == "postgres"


def test_memory_lifecycle():
    store = MemoryRecommendationStore()
    rid = new_recommendation_id()
    rec = RecommendationRecord(
        recommendation_id=rid,
        agent_id="demo",
        subjects={"job_id": "j-1", "cluster_id": "c-1"},
        status="proposed",
        response={"recommendation": {"max_workers": 8}},
    )
    store.save(rec)
    assert store.get(rid).subject("job_id") == "j-1"
    listed = store.list(subjects={"job_id": "j-1"})
    assert len(listed) == 1
    updated = store.update_status(rid, "accepted")
    assert updated is not None
    assert updated.status == "accepted"
    with pytest.raises(ValueError):
        store.update_status(rid, "bogus")


def test_none_store_discards():
    store = create_recommendation_store("none")
    assert store.name == "none"
    rid = new_recommendation_id()
    store.save(
        RecommendationRecord(
            recommendation_id=rid,
            agent_id="demo",
            subjects={"job_id": "j-1"},
            status="proposed",
        )
    )
    assert store.get(rid) is None
    assert store.list() == []


def test_configure_from_env(monkeypatch):
    monkeypatch.setenv("EDIM_RECOMMENDATION_STORE", "memory")
    s = configure_recommendation_store_from_env()
    assert s.name == "memory"
    assert get_recommendation_store().name == "memory"
    clear_recommendation_store()
    set_recommendation_store(create_recommendation_store("none"))


def test_from_dict_folds_legacy_top_level_subjects():
    rec = RecommendationRecord.from_dict(
        {
            "recommendation_id": "r1",
            "agent_id": "demo",
            "job_id": "j-legacy",
            "cluster_id": "c-legacy",
            "status": "proposed",
        }
    )
    assert rec.subjects["job_id"] == "j-legacy"
    assert rec.subjects["cluster_id"] == "c-legacy"
