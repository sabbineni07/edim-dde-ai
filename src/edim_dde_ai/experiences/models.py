"""Backend-neutral experience document model for the retrieval corpus.

Business purpose
----------------
``ExperienceDocument`` is the shape domain transforms emit and the indexing
layer upserts into a ``RetrievalProvider``. It is a **derived** view of a
``RecommendationRecord`` — never the system of record.

How it fits the platform
------------------------
``doc_id`` is keyed to ``recommendation_id`` so re-saves and status updates
are idempotent upserts (no duplicate index rows for the same lifecycle row).

Public API
----------
* ``ExperienceDocument`` — dataclass + ``to_dict`` / ``from_dict``
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExperienceDocument:
    """Canonical feature/action card indexed into a RetrievalProvider corpus.

    ``RecommendationStore`` remains the system of record. This document is a
    **derived** artifact: upsert by ``doc_id`` (== ``recommendation_id``) so
    re-saves never create duplicate index rows for the same record.

    Attributes:
        doc_id: Stable index key; conventionally ``recommendation_id``.
        corpus: Retrieval corpus name (e.g. ``spark-rca-outcomes``).
        text: Embeddable / searchable body (features + outcome narrative).
        feature_labels: Open-vocabulary labels for display and query hints.
        action_signature: Stable fingerprint of the recommended action (dedupe).
        metadata: Escape hatch (``job_id``, agent fields, occurrence hints, …).
        source: Optional provenance string for retrieval hit display.
    """

    doc_id: str
    corpus: str
    text: str
    feature_labels: list[str] = field(default_factory=list)
    action_signature: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging / transport (plain dict)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperienceDocument:
        """Rehydrate from a dict (tolerates legacy ``situation_labels``).

        Args:
            data: Serialized card; missing fields become empty defaults.

        Returns:
            A new ``ExperienceDocument`` instance.
        """
        return cls(
            doc_id=str(data.get("doc_id") or ""),
            corpus=str(data.get("corpus") or ""),
            text=str(data.get("text") or ""),
            feature_labels=[
                str(s)
                for s in (
                    data.get("feature_labels")
                    or data.get("situation_labels")  # legacy serialized cards
                    or []
                )
            ],
            action_signature=str(data.get("action_signature") or ""),
            metadata=dict(data.get("metadata") or {}),
            source=(str(data["source"]) if data.get("source") is not None else None),
        )
