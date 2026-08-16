"""Backend-agnostic evaluation models for deterministic and model-based rubrics.

Business purpose:
  Normalize evaluator output so hosts, stores, and UIs can treat rubrics and
  LLM judges uniformly (score, confidence, pass/fail, dimension breakdown).

Public API:
  - ``EvaluationResult`` — dataclass with ``quality_label`` and ``to_dict()``
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    """One evaluator's normalized result.

    ``score`` measures rubric quality (typically 0..1). ``confidence`` measures
    how complete and reliable the evidence available to the evaluator was; it is
    **not** an LLM self-reported probability.

    Attributes:
        evaluator: Evaluator name that produced this result.
        score: Quality score (conventionally 0..1).
        confidence: Evidence completeness / reliability (conventionally 0..1).
        passed: Whether the rubric threshold was met.
        dimensions: Optional per-criterion scores.
        findings: Human-readable notes / failure reasons.
        metadata: Free-form backend-specific extras.
    """

    evaluator: str
    score: float
    confidence: float
    passed: bool
    dimensions: dict[str, float] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def quality_label(self) -> str:
        """Coarse band: ``high`` (>=0.85), ``medium`` (>=0.65), else ``low``."""
        if self.score >= 0.85:
            return "high"
        if self.score >= 0.65:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        """Serialize including computed ``quality_label``.

        Returns:
            Plain dict suitable for JSON / store payloads.
        """
        return {**asdict(self), "quality_label": self.quality_label}
