"""In-memory retrieval (tests / demos without FAISS files)."""

from __future__ import annotations

import math
import re
from collections import defaultdict

from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest

_TOKEN = re.compile(r"[a-z0-9_]+", re.I)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


class MemoryRetrieval:
    """Simple TF-style overlap search over an in-process document bag."""

    def __init__(self) -> None:
        # corpus -> doc_id -> hit payload
        self._docs: dict[str, dict[str, RetrievalHit]] = defaultdict(dict)

    @property
    def name(self) -> str:
        return "memory"

    def ping(self) -> bool:
        return True

    def upsert(
        self,
        *,
        corpus: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> None:
        self._docs[corpus][doc_id] = RetrievalHit(
            id=doc_id,
            text=text,
            score=0.0,
            metadata=dict(metadata or {}),
            source=source,
        )

    def delete(self, *, corpus: str, doc_id: str) -> bool:
        bag = self._docs.get(corpus) or {}
        if doc_id in bag:
            del bag[doc_id]
            return True
        return False

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        bag = self._docs.get(request.corpus) or {}
        if not bag or not (request.query or "").strip():
            return []
        q = set(_tokens(request.query))
        if not q:
            return []
        scored: list[RetrievalHit] = []
        for hit in bag.values():
            dt = set(_tokens(hit.text))
            if not dt:
                continue
            overlap = len(q & dt)
            if overlap == 0:
                continue
            score = overlap / math.sqrt(len(q) * len(dt))
            scored.append(
                RetrievalHit(
                    id=hit.id,
                    text=hit.text,
                    score=float(score),
                    metadata=dict(hit.metadata),
                    source=hit.source,
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[: max(1, int(request.top_k))]
