"""Backfill experience / outcomes corpora from RecommendationStore rows.

Business purpose
----------------
After deploying Azure AI Search (or wiping an index), existing lifecycle rows
must be replayed through the same ``maybe_index_experience`` path used on
live saves — never by dumping raw store JSON into the index.

How it fits the platform
------------------------
* Reuses registered ``ExperienceTransform`` + status gates
* Job/CLI friendly: ``python -m edim_dde_ai.experiences.backfill``
* Fail-open per row; returns a capped error summary

Public API
----------
* ``BackfillResult`` — counts + capped errors
* ``backfill_outcomes_from_store`` — scan store and index
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from typing import Any

from edim_dde_ai.experiences.indexing import indexable_statuses, maybe_index_experience
from edim_dde_ai.experiences.registry import get_experience_transform

logger = logging.getLogger(__name__)


@dataclass
class BackfillResult:
    """Summary of a backfill run.

    Attributes:
        scanned: Rows read from the store.
        indexed: Successful ``maybe_index_experience`` upserts/deletes.
        skipped: Rows with no transform / non-indexable / empty doc / dry-run miss.
        failed: Rows that raised or returned false unexpectedly after attempt.
        errors: Capped human-readable failure strings.
        dry_run: Whether writes were skipped.
    """

    scanned: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logs / Job output."""
        return {
            "scanned": self.scanned,
            "indexed": self.indexed,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": list(self.errors),
            "dry_run": self.dry_run,
        }


def backfill_outcomes_from_store(
    *,
    agent_id: str | None = None,
    statuses: frozenset[str] | None = None,
    limit: int = 500,
    dry_run: bool = False,
    store: Any | None = None,
    max_errors: int = 20,
) -> BackfillResult:
    """Replay store rows through ``maybe_index_experience``.

    Args:
        agent_id: When set, only that agent's rows (and transform).
        statuses: Statuses to scan; default ``indexable_statuses()``.
        limit: Max rows to pull from ``store.list``.
        dry_run: Count would-index transforms without writing.
        store: Optional RecommendationStore; defaults to process registry.
        max_errors: Cap on ``errors`` list length.

    Returns:
        ``BackfillResult`` with counts.

    Example:
        >>> backfill_outcomes_from_store(agent_id="cluster_tuning", dry_run=True)  # doctest: +SKIP
    """
    if store is None:
        from edim_dde_ai.recommendations import get_recommendation_store

        store = get_recommendation_store()

    want = statuses if statuses is not None else indexable_statuses()
    result = BackfillResult(dry_run=dry_run)

    kwargs: dict[str, Any] = {"limit": max(1, int(limit))}
    if agent_id:
        kwargs["agent_id"] = agent_id
    rows = list(store.list(**kwargs))
    result.scanned = len(rows)

    for record in rows:
        status = str(getattr(record, "status", "") or "").strip().lower()
        if status not in want:
            result.skipped += 1
            continue
        transform = get_experience_transform(record.agent_id)
        if transform is None:
            result.skipped += 1
            continue
        if dry_run:
            doc = transform.transform(record)
            if doc is None or not (doc.text or "").strip():
                result.skipped += 1
            else:
                result.indexed += 1
            continue
        try:
            ok = maybe_index_experience(record)
            if ok:
                result.indexed += 1
            else:
                result.skipped += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            if len(result.errors) < max_errors:
                result.errors.append(
                    f"{getattr(record, 'recommendation_id', '?')}: {exc}"
                )
            logger.warning("backfill row failed: %s", exc)

    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry for Jobs: configure env, then backfill."""
    parser = argparse.ArgumentParser(
        description="Backfill experience outcomes from RecommendationStore"
    )
    parser.add_argument("--agent-id", default=None, help="Optional agent filter")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    # Match API lifespan so RetrievalProvider + store resolve from env.
    try:
        from edim_dde_ai.retrieval import configure_retrieval_from_env

        configure_retrieval_from_env()
    except Exception as exc:  # noqa: BLE001
        logger.warning("configure_retrieval_from_env: %s", exc)
    try:
        from edim_dde_ai.recommendations import configure_recommendation_store_from_env

        configure_recommendation_store_from_env()
    except Exception as exc:  # noqa: BLE001
        logger.warning("configure_recommendation_store_from_env: %s", exc)
    try:
        # Domain transforms register at bootstrap when package is installed.
        from edim_dde_domain.bootstrap import bootstrap_agents

        bootstrap_agents()
    except Exception as exc:  # noqa: BLE001
        logger.warning("domain bootstrap skipped/failed: %s", exc)

    summary = backfill_outcomes_from_store(
        agent_id=args.agent_id,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    print(summary.to_dict())
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
