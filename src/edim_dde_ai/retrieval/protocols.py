"""Pluggable retrieval / similarity-search provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest


@runtime_checkable
class RetrievalProvider(Protocol):
    """Backend for similarity / hybrid search (not full RAG).

    RAG = retrieve (this protocol) + inject into prompt + LLM.
    Graph YAML remains the place that composes those steps.
    """

    @property
    def name(self) -> str:
        """Stable id: none | memory | faiss | azure_ai_search | databricks_vector."""

    def ping(self) -> bool:
        """Return True if the backend is reachable / usable."""

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        """Return ranked hits for the query (may be empty)."""

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        """Index or update one document/chunk (optional for read-only backends)."""

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        """Remove a document; return True if removed."""
