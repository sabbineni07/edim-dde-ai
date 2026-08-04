"""Databricks Vector Search retrieval provider (per-corpus override)."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest

logger = logging.getLogger(__name__)


class DatabricksVectorRetrieval:
    """Query a Databricks Vector Search index.

    Install: ``pip install 'edim-dde-ai[databricks-vector]'``
    (databricks-vectorsearch + databricks-sdk).

    Env:
      - ``DATABRICKS_HOST`` — workspace host
      - ``DATABRICKS_TOKEN`` — PAT / SP token (or Apps user token path later)
      - ``EDIM_DBX_VS_ENDPOINT`` — Vector Search endpoint name
      - ``EDIM_DBX_VS_INDEX`` — default index name
      - ``EDIM_DBX_VS_CORPUS_MAP`` — optional ``corpus:index,...`` overrides
      - ``EDIM_DBX_VS_TEXT_COLUMN`` — text column (default ``text``)
      - ``EDIM_DBX_VS_ID_COLUMN`` — id column (default ``id``)
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        default_index: str | None = None,
        corpus_indexes: dict[str, str] | None = None,
    ) -> None:
        try:
            from databricks.vector_search.client import VectorSearchClient
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RETRIEVAL=databricks_vector requires databricks-vectorsearch. "
                "Install: pip install 'edim-dde-ai[databricks-vector]'"
            ) from exc

        self._endpoint = (
            endpoint or os.environ.get("EDIM_DBX_VS_ENDPOINT") or ""
        ).strip()
        self._default_index = (
            default_index or os.environ.get("EDIM_DBX_VS_INDEX") or ""
        ).strip()
        if not self._endpoint or not self._default_index:
            raise RuntimeError(
                "Databricks Vector Search requires EDIM_DBX_VS_ENDPOINT and "
                "EDIM_DBX_VS_INDEX"
            )
        self._corpus_indexes = dict(corpus_indexes or {})
        raw_map = os.environ.get("EDIM_DBX_VS_CORPUS_MAP", "").strip()
        if raw_map:
            for part in raw_map.split(","):
                if ":" not in part:
                    continue
                c, idx = part.split(":", 1)
                self._corpus_indexes[c.strip()] = idx.strip()

        self._text_col = os.environ.get("EDIM_DBX_VS_TEXT_COLUMN", "text").strip()
        self._id_col = os.environ.get("EDIM_DBX_VS_ID_COLUMN", "id").strip()
        self._client = VectorSearchClient()

    @property
    def name(self) -> str:
        return "databricks_vector"

    def _index_name(self, corpus: str) -> str:
        return self._corpus_indexes.get(corpus) or self._default_index

    def ping(self) -> bool:
        idx = self._client.get_index(
            endpoint_name=self._endpoint, index_name=self._default_index
        )
        _ = idx
        return True

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        index = self._client.get_index(
            endpoint_name=self._endpoint,
            index_name=self._index_name(request.corpus),
        )
        # similarity_search API: query_text for hybrid/managed embeddings indexes
        raw: Any
        try:
            raw = index.similarity_search(
                query_text=request.query,
                columns=[self._id_col, self._text_col],
                num_results=max(1, int(request.top_k)),
            )
        except TypeError:
            # Older SDK shape
            raw = index.similarity_search(
                query_text=request.query,
                columns=[self._id_col, self._text_col],
                num_results=max(1, int(request.top_k)),
            )

        rows = []
        if isinstance(raw, dict):
            rows = (
                raw.get("result", {}).get("data_array")
                or raw.get("data_array")
                or raw.get("manifest", {}).get("columns")
                or []
            )
            # Newer clients may return column-oriented results; normalize.
            if rows and isinstance(rows[0], dict):
                pass
            elif "data_array" in (raw.get("result") or {}):
                rows = raw["result"]["data_array"]
        elif isinstance(raw, list):
            rows = raw

        hits: list[RetrievalHit] = []
        for i, row in enumerate(rows):
            if isinstance(row, dict):
                doc_id = str(row.get(self._id_col) or row.get("id") or i)
                text = str(row.get(self._text_col) or row.get("text") or "")
                score = float(row.get("score") or row.get("_score") or 0.0)
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                doc_id, text = str(row[0]), str(row[1])
                score = float(row[2]) if len(row) > 2 else 0.0
            else:
                continue
            hits.append(
                RetrievalHit(
                    id=doc_id,
                    text=text,
                    score=score,
                    metadata={},
                    source=None,
                )
            )
        return hits[: max(1, int(request.top_k))]

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        raise NotImplementedError(
            "Databricks Vector Search upsert is owned by platform Jobs "
            "(Delta sync / VS index pipeline). Use the Jobs path for ingest."
        )

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        raise NotImplementedError(
            "Databricks Vector Search delete is owned by platform Jobs."
        )
