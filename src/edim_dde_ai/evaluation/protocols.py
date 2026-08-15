"""Evaluator Strategy protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from edim_dde_ai.evaluation.models import EvaluationResult


@runtime_checkable
class Evaluator(Protocol):
    """Evaluate one agent output against inputs and optional context."""

    @property
    def name(self) -> str: ...

    def evaluate(
        self,
        *,
        inputs: dict[str, Any],
        output: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> EvaluationResult: ...
