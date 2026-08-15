from __future__ import annotations

import pytest

from edim_dde_ai.evaluation import (
    EvaluationResult,
    clear_evaluators,
    evaluate,
    list_evaluators,
    register_evaluator,
)


class _AlwaysGood:
    @property
    def name(self) -> str:
        return "test.good"

    def evaluate(self, *, inputs, output, context=None):
        return EvaluationResult(
            evaluator=self.name,
            score=0.9,
            confidence=0.8,
            passed=True,
            dimensions={"contract": 1.0},
        )


def test_evaluator_registry_and_result_label():
    clear_evaluators()
    register_evaluator(_AlwaysGood())
    assert list_evaluators() == ["test.good"]
    result = evaluate("test.good", inputs={}, output={})
    assert result.passed
    assert result.quality_label == "high"
    assert result.to_dict()["quality_label"] == "high"


def test_unknown_evaluator_is_explicit():
    clear_evaluators()
    with pytest.raises(KeyError, match="Unknown evaluator"):
        evaluate("missing", inputs={}, output={})
