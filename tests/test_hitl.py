"""HITL gate pause + resume against StateStore sessions."""

from __future__ import annotations

import pytest

from edim_dde_ai.api.entrypoints import register_from_dict
from edim_dde_ai.errors import HitlError
from edim_dde_ai.hitl import resume_hitl_session
from edim_dde_ai.registry.agents import create_agent
from edim_dde_ai.store import MemoryStateStore, get_state_store, set_state_store


HITL_AGENT = {
    "agent_id": "hitl_unit_demo",
    "display_name": "HITL unit demo",
    "version": 1,
    "metadata": {"hitl_required": True, "risk_tier": "low", "lifecycle": "draft"},
    "hitl": {"enabled": True},
    "graph": {
        "nodes": [
            {
                "id": "draft",
                "type": "set_value",
                "field": "proposal",
                "template": "resize-{name}",
            },
            {
                "id": "approve",
                "type": "hitl.gate",
                "prompt": "Approve?",
            },
            {
                "id": "finish",
                "type": "set_value",
                "field": "status",
                "template": "done:{hitl_decision}",
            },
        ],
        "edges": [
            ["START", "draft"],
            ["draft", "approve"],
            ["approve", "finish"],
            ["finish", "END"],
        ],
    },
}


@pytest.fixture
def hitl_store():
    store = MemoryStateStore()
    set_state_store(store)
    register_from_dict(HITL_AGENT, overwrite=True)
    yield store
    set_state_store(MemoryStateStore())


def test_hitl_pause_persists_waiting_session(hitl_store):
    out = create_agent("hitl_unit_demo").invoke({"name": "alpha"})
    assert out["hitl_status"] == "waiting_hitl"
    assert out["proposal"] == "resize-alpha"
    assert "status" not in out or out.get("status") != "done:approved"
    sid = out["session_id"]
    rec = get_state_store().get_session(sid)
    assert rec is not None
    assert rec.status == "waiting_hitl"
    assert rec.agent_id == "hitl_unit_demo"


def test_hitl_resume_skips_nodes_before_gate(hitl_store):
    paused = create_agent("hitl_unit_demo").invoke({"name": "alpha"})
    sid = paused["session_id"]
    out = resume_hitl_session(
        sid,
        decision="approved",
        comment="looks good",
        patch={"name": "beta"},
    )
    assert out["hitl_decision"] == "approved"
    assert out["status"] == "done:approved"
    assert out["proposal"] == "resize-alpha"
    rec = get_state_store().get_session(sid)
    assert rec is not None
    assert rec.status == "closed"


def test_hitl_resume_rejected(hitl_store):
    paused = create_agent("hitl_unit_demo").invoke({"name": "alpha"})
    out = resume_hitl_session(paused["session_id"], decision="rejected")
    assert out["status"] == "done:rejected"


def test_hitl_resume_invalid_decision(hitl_store):
    paused = create_agent("hitl_unit_demo").invoke({"name": "alpha"})
    with pytest.raises(HitlError, match="decision"):
        resume_hitl_session(paused["session_id"], decision="maybe")


def test_hitl_resume_wrong_status(hitl_store):
    paused = create_agent("hitl_unit_demo").invoke({"name": "alpha"})
    resume_hitl_session(paused["session_id"], decision="approved")
    with pytest.raises(HitlError, match="waiting_hitl"):
        resume_hitl_session(paused["session_id"], decision="approved")


def test_skip_until_resume_decorator():
    from edim_dde_ai.hitl.decorator import RESUME_AT_KEY, skip_until_resume

    calls: list[str] = []

    def _draft(state: dict) -> dict:
        calls.append("draft")
        return {"proposal": "x"}

    wrapped = skip_until_resume("draft", _draft)
    assert wrapped({RESUME_AT_KEY: "approve"}) == {}
    assert calls == []
    assert wrapped({"name": "a"}) == {"proposal": "x"}
    assert calls == ["draft"]
    assert wrapped({RESUME_AT_KEY: "draft"}) == {"proposal": "x"}


def test_prior_decision_and_merge_helpers():
    from edim_dde_ai.hitl.sessions import (
        merge_hitl_decision,
        prior_decision_for_gate,
    )

    state = {"proposal": "resize-a"}
    assert prior_decision_for_gate(state, "approve") is None
    merged = merge_hitl_decision(
        state,
        session_id="s1",
        gate_id="approve",
        decision="approved",
        comment="ok",
        patch={"name": "b"},
        actor="analyst",
    )
    prior = prior_decision_for_gate(merged, "approve")
    assert prior is not None
    assert prior["decision"] == "approved"
    assert prior["comment"] == "ok"
    assert merged["name"] == "b"
    assert merged["hitl_resume_at"] == "approve"


def test_hitl_gate_noop_when_disabled():
    set_state_store(MemoryStateStore())
    data = dict(HITL_AGENT)
    data["agent_id"] = "hitl_disabled_demo"
    data["hitl"] = {"enabled": False}
    register_from_dict(data, overwrite=True)
    out = create_agent("hitl_disabled_demo").invoke({"name": "z"})
    assert out.get("hitl_status") != "waiting_hitl"
    assert out["proposal"] == "resize-z"
