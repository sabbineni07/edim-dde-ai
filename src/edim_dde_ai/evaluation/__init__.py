"""Agent-output evaluation (deterministic rubrics or model-based evaluators).

Business purpose:
  Hosts and product agents register named ``Evaluator`` strategies, then call
  ``evaluate(name, inputs=..., output=...)`` to score a run against a rubric.
  Results are backend-agnostic (``EvaluationResult``).

Public API:
  - ``EvaluationResult`` — normalized score / confidence / findings
  - ``Evaluator`` — Strategy protocol
  - ``register_evaluator`` / ``get_evaluator`` / ``list_evaluators`` / ``clear_evaluators``
  - ``evaluate`` — look up by name and run
"""

from edim_dde_ai.evaluation.models import EvaluationResult
from edim_dde_ai.evaluation.protocols import Evaluator
from edim_dde_ai.evaluation.registry import (
    clear_evaluators,
    evaluate,
    get_evaluator,
    list_evaluators,
    register_evaluator,
)

__all__ = [
    "EvaluationResult",
    "Evaluator",
    "clear_evaluators",
    "evaluate",
    "get_evaluator",
    "list_evaluators",
    "register_evaluator",
]
