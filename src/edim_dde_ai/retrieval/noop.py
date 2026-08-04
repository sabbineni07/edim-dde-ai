"""No-op retrieval provider (default when EDIM_RETRIEVAL=none)."""

from __future__ import annotations

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest


class NoOpRetrieval:
    """Disables retrieval — search always returns []."""

    @property
    def name(self) -> str:
        return "none"

    def ping(self) -> bool:
        return True

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
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
        return None

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        return False
