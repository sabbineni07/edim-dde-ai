"""Tests for recommendation outcome scaffolding."""

from edim_dde_ai.recommendations.outcome import merge_outcome_extra


def test_merge_outcome_extra_keeps_product_keys_in_updates():
    extra = merge_outcome_extra(
        {"keep": 1},
        human_label="ok",
        labeled_by="bob",
        updates={"ticket_id": "INC-1", "rerun_success": True},
    )
    assert extra["keep"] == 1
    assert extra["outcome"]["human_label"] == "ok"
    assert extra["outcome"]["labeled_by"] == "bob"
    assert "labeled_at" in extra["outcome"]
    assert extra["outcome"]["ticket_id"] == "INC-1"
    assert extra["outcome"]["rerun_success"] is True
