"""Experience documents — derived view of recommendations for similarity search."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExperienceDocument:
    """Canonical situation/action card indexed into a RetrievalProvider corpus.

    ``RecommendationStore`` remains the system of record. This document is a
    **derived** artifact: upsert by ``doc_id`` (== ``recommendation_id``) so
    re-saves never create duplicate index rows for the same record.
    """

    doc_id: str
    corpus: str
    text: str
    situation_labels: list[str] = field(default_factory=list)
    action_signature: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperienceDocument:
        return cls(
            doc_id=str(data.get("doc_id") or ""),
            corpus=str(data.get("corpus") or ""),
            text=str(data.get("text") or ""),
            situation_labels=[str(s) for s in (data.get("situation_labels") or [])],
            action_signature=str(data.get("action_signature") or ""),
            metadata=dict(data.get("metadata") or {}),
            source=(str(data["source"]) if data.get("source") is not None else None),
        )
