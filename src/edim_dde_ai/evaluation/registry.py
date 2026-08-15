"""Process-wide evaluator registry (Strategy + Registry)."""

from __future__ import annotations

from typing import Any

from edim_dde_ai.evaluation.models import EvaluationResult
from edim_dde_ai.evaluation.protocols import Evaluator

_EVALUATORS: dict[str, Evaluator] = {}


def register_evaluator(evaluator: Evaluator) -> None:
    name = str(evaluator.name).strip()
    if not name:
        raise ValueError("Evaluator.name must be non-empty")
    _EVALUATORS[name] = evaluator


def get_evaluator(name: str) -> Evaluator | None:
    return _EVALUATORS.get(str(name).strip())


def list_evaluators() -> list[str]:
    return sorted(_EVALUATORS)


def clear_evaluators() -> None:
    _EVALUATORS.clear()


def evaluate(
    name: str,
    *,
    inputs: dict[str, Any],
    output: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> EvaluationResult:
    evaluator = get_evaluator(name)
    if evaluator is None:
        raise KeyError(f"Unknown evaluator {name!r}; registered={list_evaluators()}")
    return evaluator.evaluate(inputs=inputs, output=output, context=context)
