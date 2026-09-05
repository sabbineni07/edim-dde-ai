"""Tests for YAML-driven HITL policy helpers."""

from __future__ import annotations

import pytest

from edim_dde_ai.errors import HitlError
from edim_dde_ai.hitl.policy import (
    allowed_decisions,
    filter_hitl_patch,
    is_hitl_waiting,
    prepare_resume_patch,
    should_persist_after_hitl,
)


def _hitl(**fields):
    return {"hitl": fields}


def test_allowed_decisions_defaults_and_intersects():
    assert "modified" in allowed_decisions(None)
    assert allowed_decisions(_hitl(decisions=["approved", "rejected"])) == frozenset(
        {"approved", "rejected"}
    )
    # Unknown tokens dropped
    assert allowed_decisions(_hitl(decisions=["approved", "maybe"])) == frozenset(
        {"approved"}
    )


def test_filter_hitl_patch_nested_and_allowlist():
    allow = frozenset({"recommended_max_workers", "vcpus"})
    assert filter_hitl_patch(
        {"recommendation": {"recommended_max_workers": 3, "secret": 1}},
        allow,
        target_key="recommendation",
    ) == {"recommended_max_workers": 3}
    assert filter_hitl_patch({"not_allowed": 1}, allow) == {}
    assert filter_hitl_patch({"vcpus": 8}, None) == {"vcpus": 8}


def test_prepare_resume_patch_enforces_yaml_policy():
    definition = _hitl(
        decisions=["approved", "rejected", "modified"],
        patch_allowlist=["recommended_max_workers"],
        patch_target="recommendation",
    )
    assert prepare_resume_patch(definition, decision="approved", patch=None) is None
    with pytest.raises(HitlError):
        prepare_resume_patch(definition, decision="modified", patch={"nope": 1})
    assert prepare_resume_patch(
        definition,
        decision="modified",
        patch={"recommended_max_workers": 2},
    ) == {"recommended_max_workers": 2}
    with pytest.raises(HitlError):
        prepare_resume_patch(
            _hitl(decisions=["approved", "rejected"]),
            decision="modified",
            patch={"recommended_max_workers": 2},
        )


def test_waiting_and_persist_helpers():
    assert is_hitl_waiting({"hitl_status": "waiting_hitl"})
    assert not should_persist_after_hitl({"hitl_status": "waiting_hitl"})
    assert not should_persist_after_hitl({"hitl_outcome": "rejected"})
    assert should_persist_after_hitl({"hitl_outcome": "approved", "status": "completed"})
