"""Tests for HITL persist adapter registry."""

from __future__ import annotations

from edim_dde_ai.hitl.persist import (
    clear_hitl_persist_adapters,
    list_hitl_persist_adapters,
    persist_after_hitl_if_needed,
    register_hitl_persist_adapter,
)


def setup_function() -> None:
    clear_hitl_persist_adapters()


def teardown_function() -> None:
    clear_hitl_persist_adapters()


def test_persist_adapter_runs_only_when_allowed():
    calls: list[str] = []

    def adapter(state: dict, request_id: str) -> dict:
        calls.append(request_id)
        return {**state, "recommendation_id": "rec-1"}

    register_hitl_persist_adapter("demo", adapter)
    assert list_hitl_persist_adapters() == ["demo"]

    waiting = persist_after_hitl_if_needed(
        "demo",
        {"hitl_status": "waiting_hitl"},
        request_id="r1",
    )
    assert waiting.get("recommendation_id") is None
    assert calls == []

    rejected = persist_after_hitl_if_needed(
        "demo",
        {"hitl_outcome": "rejected", "status": "rejected"},
        request_id="r1",
    )
    assert rejected.get("recommendation_id") is None

    done = persist_after_hitl_if_needed(
        "demo",
        {"hitl_outcome": "approved", "status": "completed"},
        request_id="r2",
    )
    assert done["recommendation_id"] == "rec-1"
    assert calls == ["r2"]


def test_unknown_agent_is_noop():
    out = persist_after_hitl_if_needed(
        "missing",
        {"hitl_outcome": "approved"},
        request_id="r1",
    )
    assert out["hitl_outcome"] == "approved"
