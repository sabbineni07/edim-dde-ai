"""RecommendationStore ownership + generic outcome scaffolding.

``merge_outcome_extra`` only knows framework-neutral feedback fields
(``human_label`` / ``labeled_by``) plus an opaque ``updates`` map. Product
keys such as ``rerun_job_run_id`` belong in host/domain ``updates``, not as
first-class framework parameters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.registry import get_recommendation_store


def get_recommendation_for_agent(
    recommendation_id: str, agent_id: str
) -> RecommendationRecord | None:
    """Load a recommendation when it exists and is owned by ``agent_id``."""
    row = get_recommendation_store().get(recommendation_id)
    if row is None or row.agent_id != agent_id:
        return None
    return row


def merge_outcome_extra(
    extra: dict[str, Any] | None,
    *,
    human_label: str | None = None,
    labeled_by: str | None = None,
    updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge outcome scaffolding into ``RecommendationRecord.extra``.

    Framework-owned keys (optional):
        ``human_label``, ``labeled_by``, ``labeled_at`` (stamped when label set).

    Product-specific keys (jobs, SKUs, tickets, …) must be passed via
    ``updates`` so future agents are not forced into a job-run vocabulary.

    Does not mutate the input dict; returns a new mapping.
    """
    out = dict(extra or {})
    outcome = dict(out.get("outcome") or {})
    now = datetime.now(timezone.utc).isoformat()
    if human_label is not None:
        outcome["human_label"] = str(human_label).strip()
        outcome["labeled_at"] = now
        if labeled_by:
            outcome["labeled_by"] = str(labeled_by).strip()
    if updates:
        for key, value in updates.items():
            if value is None:
                continue
            outcome[str(key)] = value
    if outcome:
        out["outcome"] = outcome
    return out
