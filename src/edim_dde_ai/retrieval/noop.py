"""No-op retrieval provider (default when ``EDIM_RETRIEVAL=none``).

Business purpose
----------------
Retrieval is optional. When disabled, graphs still resolve a provider and call
``search`` without branching — this backend always returns empty hits and
ignores upsert/delete.

Public API
----------
* ``NoOpRetrieval`` — ``RetrievalProvider`` that never retrieves
"""

from __future__ import annotations

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest


class NoOpRetrieval:
    """Disables retrieval — search always returns ``[]``."""

    @property
    def name(self) -> str:
        """Backend id for health / logs (``none``)."""
        return "none"

    def ping(self) -> bool:
        """Always healthy (no external dependency).

        Returns:
            ``True``.
        """
        return True

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        """Return no hits.

        Args:
            request: Ignored (kept for protocol compatibility).

        Returns:
            Empty list.
        """
        return []

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        """No-op write (documents are discarded)."""
        return None

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        """No-op delete.

        Returns:
            ``False`` (nothing stored).
        """
        return False
