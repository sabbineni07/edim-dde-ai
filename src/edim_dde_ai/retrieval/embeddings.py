"""Lightweight hashing embedder (no cloud / no torch required).

Business purpose
----------------
Local FAISS indexes need a deterministic vectorizer that works offline in
control-plane processes and Databricks Jobs without pulling Azure OpenAI or
torch. This hash embedder is good enough for demos and runbook keyword
overlap; production ingest can swap in Foundry / Azure OpenAI embeddings.

Public API
----------
* ``HashingEmbedder`` — ``embed`` / ``embed_many`` over a fixed dimension
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Sequence

_TOKEN = re.compile(r"[a-z0-9_]+", re.I)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


class HashingEmbedder:
    """Deterministic bag-of-tokens hash embedding for local FAISS indexes.

    Good enough for demos and runbook keyword overlap; swap for Foundry /
    Azure OpenAI embeddings in production ingest Jobs when needed.
    """

    def __init__(self, dim: int = 384) -> None:
        """Create an embedder with a fixed output dimension.

        Args:
            dim: Vector length (must be ``>= 8``). FAISS indexes must use the
                same dim at build and query time.

        Raises:
            ValueError: If ``dim < 8``.
        """
        if dim < 8:
            raise ValueError("embed dim must be >= 8")
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        """Embed one string into an L2-normalized float vector.

        Args:
            text: Free-text document or query.

        Returns:
            Length-``dim`` list of floats (zeros if no tokens).
        """
        vec = [0.0] * self.dim
        toks = _tokens(text)
        if not toks:
            return vec
        for tok in toks:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        # L2 normalize so IndexFlatIP ≈ cosine similarity
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed many strings (sequential; no batching).

        Args:
            texts: Sequence of free-text strings.

        Returns:
            List of vectors in the same order as ``texts``.
        """
        return [self.embed(t) for t in texts]
