"""Backend-agnostic evaluation models for deterministic and model-based rubrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    """One evaluator's normalized result.

    ``score`` measures rubric quality. ``confidence`` measures how complete and
    reliable the evidence available to the evaluator was; it is **not** an LLM
    self-reported probability.
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
        if self.score >= 0.85:
            return "high"
        if self.score >= 0.65:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "quality_label": self.quality_label}
