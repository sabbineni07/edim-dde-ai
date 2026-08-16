"""Strategy protocol for pluggable retrieval / similarity-search backends.

Business purpose
----------------
Hosts inject a concrete ``RetrievalProvider`` at process start
(``configure_retrieval_from_env`` or ``set_retrieval_provider``). Graph nodes
and domain helpers depend only on this protocol so unit tests can swap in
``MemoryRetrieval`` or ``NoOpRetrieval``.

Public API
----------
* ``RetrievalProvider`` — ``name``, ``ping``, ``search``, ``upsert``, ``delete``

RAG = retrieve (this protocol) + inject into prompt + LLM. Graph YAML remains
the place that composes those steps; this module only defines the retrieve step.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest


@runtime_checkable
class RetrievalProvider(Protocol):
    """Backend for similarity / hybrid search (not full RAG).

    Implementations should be safe to call from request threads. Empty hit
    lists are success ("nothing found"); transport failures may raise — callers
    such as builtin retrieve nodes typically catch and fail-open.
    """

    @property
    def name(self) -> str:
        """Stable backend id for health / logs.

        Returns:
            One of ``none`` | ``memory`` | ``faiss`` | ``azure_ai_search`` |
            ``databricks_vector`` (or a custom id for host-owned wrappers).
        """

    def ping(self) -> bool:
        """Return whether the backend is reachable / usable.

        Returns:
            ``True`` when a lightweight health check succeeds.
        """

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        """Return ranked hits for the query (may be empty).

        Args:
            request: Normalized query, corpus, ``top_k``, mode, and filters.

        Returns:
            Score-ordered ``RetrievalHit`` rows, ideally truncated to
            ``request.top_k``.
        """

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        """Index or update one document/chunk.

        Optional for read-only backends (e.g. Databricks Vector Search may
        raise ``NotImplementedError`` and expect Jobs-owned ingest).

        Args:
            corpus: Logical corpus name (maps to index / file set).
            doc_id: Stable document or chunk id within the corpus.
            text: Body text to embed / index.
            metadata: Optional opaque fields returned on search hits.
            source: Optional human-readable origin (path, URI).
        """

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        """Remove a document from the corpus index.

        Args:
            corpus: Logical corpus name.
            doc_id: Document id previously upserted.

        Returns:
            ``True`` if a row was removed; ``False`` if missing (or no-op).
        """
