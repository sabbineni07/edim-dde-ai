"""Process-wide evaluator registry (Strategy + Registry).

Business purpose:
  Catalog of named evaluators shared across the process. Product code registers
  implementations at startup; hosts invoke by string name.

Public API:
  - ``register_evaluator(evaluator)``
  - ``get_evaluator(name)``
  - ``list_evaluators()``
  - ``clear_evaluators()``
  - ``evaluate(name, *, inputs, output, context=None)``
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.evaluation.models import EvaluationResult
from edim_dde_ai.evaluation.protocols import Evaluator

_EVALUATORS: dict[str, Evaluator] = {}


def register_evaluator(evaluator: Evaluator) -> None:
    """Install ``evaluator`` under ``evaluator.name`` (overwrites same name).

    Args:
        evaluator: Object implementing the ``Evaluator`` protocol.

    Raises:
        ValueError: If ``evaluator.name`` is empty after strip.
    """
    name = str(evaluator.name).strip()
    if not name:
        raise ValueError("Evaluator.name must be non-empty")
    _EVALUATORS[name] = evaluator


def get_evaluator(name: str) -> Evaluator | None:
    """Return the registered evaluator for ``name``, or ``None``.

    Args:
        name: Evaluator id (whitespace-stripped).

    Returns:
        The ``Evaluator`` instance, or ``None`` if unknown.
    """
    return _EVALUATORS.get(str(name).strip())


def list_evaluators() -> list[str]:
    """Return sorted registered evaluator names."""
    return sorted(_EVALUATORS)


def clear_evaluators() -> None:
    """Remove all evaluators (tests / process reset)."""
    _EVALUATORS.clear()


def evaluate(
    name: str,
    *,
    inputs: dict[str, Any],
    output: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> EvaluationResult:
    """Look up ``name`` and run ``evaluator.evaluate(...)``.

    Args:
        name: Registered evaluator id.
        inputs: Original agent / task inputs.
        output: Agent output (flat dict).
        context: Optional extra evidence (retrieved docs, labels, …).

    Returns:
        Normalized ``EvaluationResult``.

    Raises:
        KeyError: If ``name`` is not registered.

    Example::

        register_evaluator(MyRubric())
        result = evaluate("my_rubric", inputs={"q": "..."}, output={"answer": "..."})
    """
    evaluator = get_evaluator(name)
    if evaluator is None:
        raise KeyError(f"Unknown evaluator {name!r}; registered={list_evaluators()}")
    return evaluator.evaluate(inputs=inputs, output=output, context=context)
