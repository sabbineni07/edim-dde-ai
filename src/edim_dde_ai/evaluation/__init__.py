"""Agent-output evaluation (deterministic rubrics or model-based evaluators)."""

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
