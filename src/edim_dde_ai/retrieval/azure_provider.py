"""Azure AI Search retrieval provider (deployed default).

Business purpose
----------------
Production / SDBX hosts typically point ``EDIM_RETRIEVAL=azure_ai_search`` so
agents query managed indexes instead of local FAISS files. Logical corpora map
to index names via constructor args, ``CorpusConfig.azure_index``, or
``EDIM_AZURE_SEARCH_CORPUS_MAP``.

Public API
----------
* ``AzureAISearchRetrieval`` — ``RetrievalProvider`` over Azure AI Search

Install: ``pip install 'edim-dde-ai[azure-search]'``

Env
---
* ``EDIM_AZURE_SEARCH_ENDPOINT`` — ``https://{service}.search.windows.net``
* ``EDIM_AZURE_SEARCH_KEY`` — admin or query key (Key Vault in PROD)
* ``EDIM_AZURE_SEARCH_INDEX`` — default index when corpus has no override
* ``EDIM_AZURE_SEARCH_CORPUS_MAP`` — optional ``corpus:index,...`` overrides
"""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest

logger = logging.getLogger(__name__)


class AzureAISearchRetrieval:
    """Similarity / hybrid search via Azure AI Search.

    Install: ``pip install 'edim-dde-ai[azure-search]'``

    Env:
      - ``EDIM_AZURE_SEARCH_ENDPOINT`` — https://{service}.search.windows.net
      - ``EDIM_AZURE_SEARCH_KEY`` — admin or query key (Key Vault in PROD)
      - ``EDIM_AZURE_SEARCH_INDEX`` — default index when corpus has no override
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        key: str | None = None,
        default_index: str | None = None,
        corpus_indexes: dict[str, str] | None = None,
    ) -> None:
        """Build a Search client factory from args or environment.

        Args:
            endpoint: Service URL; defaults to ``EDIM_AZURE_SEARCH_ENDPOINT``.
            key: API key; defaults to ``EDIM_AZURE_SEARCH_KEY``.
            default_index: Fallback index name.
            corpus_indexes: Explicit ``corpus → index`` map (merged with
                ``EDIM_AZURE_SEARCH_CORPUS_MAP``).

        Raises:
            RuntimeError: Missing ``azure-search-documents`` or required env.
        """
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RETRIEVAL=azure_ai_search requires azure-search-documents. "
                "Install: pip install 'edim-dde-ai[azure-search]'"
            ) from exc

        endpoint = (
            endpoint or os.environ.get("EDIM_AZURE_SEARCH_ENDPOINT") or ""
        ).strip()
        key = (key or os.environ.get("EDIM_AZURE_SEARCH_KEY") or "").strip()
        if not endpoint or not key:
            raise RuntimeError(
                "Azure AI Search requires EDIM_AZURE_SEARCH_ENDPOINT and "
                "EDIM_AZURE_SEARCH_KEY"
            )
        self._endpoint = endpoint.rstrip("/")
        self._credential = AzureKeyCredential(key)
        self._SearchClient = SearchClient
        self._default_index = (
            default_index
            or os.environ.get("EDIM_AZURE_SEARCH_INDEX")
            or ""
        ).strip()
        self._corpus_indexes = dict(corpus_indexes or {})
        # Optional: EDIM_AZURE_SEARCH_CORPUS_MAP=spark-runbooks:idx1,other:idx2
        raw_map = os.environ.get("EDIM_AZURE_SEARCH_CORPUS_MAP", "").strip()
        if raw_map:
            for part in raw_map.split(","):
                if ":" not in part:
                    continue
                c, idx = part.split(":", 1)
                self._corpus_indexes[c.strip()] = idx.strip()

    @property
    def name(self) -> str:
        """Backend id for health / logs (``azure_ai_search``)."""
        return "azure_ai_search"

    def _index_for(self, corpus: str) -> str:
        return self._corpus_indexes.get(corpus) or self._default_index or corpus

    def _client(self, corpus: str) -> Any:
        return self._SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_for(corpus),
            credential=self._credential,
        )

    def ping(self) -> bool:
        """Light search against the default index.

        Returns:
            ``True`` if the service accepts a trivial query.

        Raises:
            Exception: Propagated from the Azure SDK on transport/auth failure.
        """
        # Light get-document-count style call via search top=1
        client = self._client(self._default_index or "ping")
        list(client.search(search_text="*", top=1))
        return True

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        """Run text (keyword/semantic) search; vector mode falls back to text.

        Field mapping prefers ``content`` / ``text`` / ``chunk`` / ``summary``
        for body and ``id`` / ``doc_id`` for document id.

        Args:
            request: Query, corpus, and ``top_k``.

        Returns:
            Normalized ``RetrievalHit`` rows from Azure documents.
        """
        client = self._client(request.corpus)
        kwargs: dict[str, Any] = {
            "search_text": request.query,
            "top": max(1, int(request.top_k)),
            "include_total_count": False,
        }
        # Prefer hybrid when SDK / index supports vector queries later;
        # keyword+semantic text search is the R1 deployed default.
        if request.search_mode == "vector":
            # Without vector query payload, fall back to text search.
            logger.debug("Azure provider: vector mode falling back to text search")
        results = client.search(**kwargs)
        hits: list[RetrievalHit] = []
        for doc in results:
            data = dict(doc)
            doc_id = str(
                data.get("id")
                or data.get("doc_id")
                or data.get("@search.action")
                or data.get("metadata_storage_path")
                or len(hits)
            )
            text = str(
                data.get("content")
                or data.get("text")
                or data.get("chunk")
                or data.get("summary")
                or ""
            )
            score = float(data.get("@search.score") or 0.0)
            source = data.get("source") or data.get("path")
            hits.append(
                RetrievalHit(
                    id=doc_id,
                    text=text,
                    score=score,
                    metadata={
                        k: v
                        for k, v in data.items()
                        if not str(k).startswith("@")
                        and k not in {"content", "text", "chunk", "id", "doc_id"}
                    },
                    source=str(source) if source is not None else None,
                )
            )
        return hits

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        """Upload one document (``id`` + ``content``/``text`` fields).

        Args:
            corpus: Logical corpus → index name.
            doc_id: Document key.
            text: Body stored as both ``content`` and ``text``.
            metadata: Merged into the document body.
            source: Optional ``source`` field.
        """
        client = self._client(corpus)
        body: dict[str, Any] = {
            "id": doc_id,
            "content": text,
            "text": text,
        }
        if source:
            body["source"] = source
        if metadata:
            body.update(metadata)
        client.upload_documents(documents=[body])

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        """Delete one document by id.

        Args:
            corpus: Logical corpus → index name.
            doc_id: Document key.

        Returns:
            ``True`` after the delete request is accepted (SDK does not
            distinguish missing ids here).
        """
        client = self._client(corpus)
        client.delete_documents(documents=[{"id": doc_id}])
        return True
