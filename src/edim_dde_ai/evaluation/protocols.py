"""Evaluator Strategy protocol.

Business purpose:
  Defines the duck-typed contract for scoring agent outputs. Implementations may
  be deterministic rubrics or model-based judges; the registry only requires
  ``name`` and ``evaluate``.

Public API:
  - ``Evaluator`` — runtime-checkable Protocol
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from edim_dde_ai.evaluation.models import EvaluationResult


@runtime_checkable
class Evaluator(Protocol):
    """Evaluate one agent output against inputs and optional context.

    Attributes:
        name: Stable registry key.

    Methods:
        evaluate: Score ``output`` given ``inputs`` / ``context``.
    """

    @property
    def name(self) -> str: ...

    def evaluate(
        self,
        *,
        inputs: dict[str, Any],
        output: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Return a normalized ``EvaluationResult``.

        Args:
            inputs: Original task / agent inputs.
            output: Agent output dict to score.
            context: Optional supporting evidence.

        Returns:
            ``EvaluationResult`` with score, confidence, findings, etc.
        """
        ...
