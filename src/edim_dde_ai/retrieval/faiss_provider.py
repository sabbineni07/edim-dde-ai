"""FAISS file-backed retrieval (local path or Databricks Volume path)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from edim_dde_ai.retrieval.embeddings import HashingEmbedder
from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest

logger = logging.getLogger(__name__)


def _corpus_paths(base: Path, corpus: str) -> tuple[Path, Path]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in corpus)
    return base / f"{safe}.faiss", base / f"{safe}.meta.json"


class FaissRetrieval:
    """Control-plane-adjacent knowledge index stored as FAISS + JSON sidecar.

    Install: ``pip install 'edim-dde-ai[faiss]'``

    Env:
      - ``EDIM_FAISS_INDEX_PATH`` — directory for ``{corpus}.faiss`` + ``.meta.json``
        (local filesystem **or** Databricks Volume, e.g.
        ``/Volumes/catalog/schema/edim_indexes``)
    """

    def __init__(
        self,
        *,
        index_dir: str | Path | None = None,
        embedder: HashingEmbedder | None = None,
    ) -> None:
        try:
            import faiss  # noqa: F401
            import numpy as np  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RETRIEVAL=faiss requires faiss-cpu and numpy. "
                "Install: pip install 'edim-dde-ai[faiss]'"
            ) from exc

        raw = (
            str(index_dir)
            if index_dir is not None
            else os.environ.get("EDIM_FAISS_INDEX_PATH", "").strip()
        )
        if not raw:
            raise RuntimeError(
                "FAISS retrieval requires EDIM_FAISS_INDEX_PATH "
                "(local directory or Databricks Volume path)"
            )
        self._dir = Path(raw).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder or HashingEmbedder(
            dim=int(os.environ.get("EDIM_FAISS_DIM", "384"))
        )
        self._faiss = __import__("faiss")
        self._np = __import__("numpy")

    @property
    def name(self) -> str:
        return "faiss"

    def ping(self) -> bool:
        return self._dir.is_dir()

    def _load(self, corpus: str) -> tuple[Any, list[dict[str, Any]]]:
        index_path, meta_path = _corpus_paths(self._dir, corpus)
        if not index_path.is_file() or not meta_path.is_file():
            index = self._faiss.IndexFlatIP(self._embedder.dim)
            return index, []
        index = self._faiss.read_index(str(index_path))
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta, list):
            raise RuntimeError(f"Corrupt FAISS meta at {meta_path}")
        return index, meta

    def _save(self, corpus: str, index: Any, meta: list[dict[str, Any]]) -> None:
        index_path, meta_path = _corpus_paths(self._dir, corpus)
        self._faiss.write_index(index, str(index_path))
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        index, meta = self._load(corpus)
        # Rebuild without this id then append (small corpora; Jobs should batch).
        kept = [m for m in meta if m.get("id") != doc_id]
        if len(kept) != len(meta):
            index, meta = self._rebuild(kept)
        vec = self._np.asarray(
            [self._embedder.embed(text)], dtype=self._np.float32
        )
        index.add(vec)
        meta.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": dict(metadata or {}),
                "source": source,
            }
        )
        self._save(corpus, index, meta)

    def _rebuild(self, meta: list[dict[str, Any]]) -> tuple[Any, list[dict[str, Any]]]:
        index = self._faiss.IndexFlatIP(self._embedder.dim)
        if not meta:
            return index, []
        vectors = self._np.asarray(
            [self._embedder.embed(str(m.get("text") or "")) for m in meta],
            dtype=self._np.float32,
        )
        index.add(vectors)
        return index, meta

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        index, meta = self._load(corpus)
        kept = [m for m in meta if m.get("id") != doc_id]
        if len(kept) == len(meta):
            return False
        index, meta = self._rebuild(kept)
        self._save(corpus, index, meta)
        return True

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        index, meta = self._load(request.corpus)
        if index.ntotal == 0 or not meta or not (request.query or "").strip():
            return []
        q = self._np.asarray(
            [self._embedder.embed(request.query)], dtype=self._np.float32
        )
        k = min(max(1, int(request.top_k)), index.ntotal)
        scores, idxs = index.search(q, k)
        hits: list[RetrievalHit] = []
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist(), strict=False):
            if idx < 0 or idx >= len(meta):
                continue
            row = meta[idx]
            hits.append(
                RetrievalHit(
                    id=str(row.get("id") or idx),
                    text=str(row.get("text") or ""),
                    score=float(score),
                    metadata=dict(row.get("metadata") or {}),
                    source=row.get("source"),
                )
            )
        # Optional keyword re-rank boost for hybrid mode
        if request.search_mode in {"hybrid", "keyword"}:
            q_terms = set(request.query.lower().split())
            for hit in hits:
                overlap = sum(1 for t in q_terms if t and t in hit.text.lower())
                hit.score = float(hit.score) + 0.05 * overlap
            hits.sort(key=lambda h: h.score, reverse=True)
        return hits


def build_faiss_index_from_dir(
    *,
    corpus: str,
    source_dir: str | Path,
    index_dir: str | Path | None = None,
    glob: str = "**/*.md",
) -> int:
    """Index markdown (or text) files into FAISS. Returns document count.

    Used by platform Jobs and local bootstrap. Paths may be local or Volumes.
    """
    provider = FaissRetrieval(index_dir=index_dir)
    root = Path(source_dir).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Source directory not found: {root}")
    count = 0
    for path in sorted(root.glob(glob)):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        rel = str(path.relative_to(root))
        provider.upsert(
            corpus=corpus,
            doc_id=rel.replace("/", "__"),
            text=text,
            metadata={"path": rel},
            source=rel,
        )
        count += 1
    logger.info("Indexed %s docs into FAISS corpus=%s dir=%s", count, corpus, index_dir)
    return count
