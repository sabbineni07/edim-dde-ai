"""Process-wide retrieval provider registry."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.retrieval.corpus import get_corpus
from edim_dde_ai.retrieval.memory import MemoryRetrieval
from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest, format_hits_as_context
from edim_dde_ai.retrieval.noop import NoOpRetrieval
from edim_dde_ai.retrieval.protocols import RetrievalProvider

logger = logging.getLogger(__name__)

_PROVIDER: RetrievalProvider = NoOpRetrieval()
# Optional per-corpus provider overrides (lazy)
_CORPUS_PROVIDERS: dict[str, RetrievalProvider] = {}


def set_retrieval_provider(provider: RetrievalProvider) -> None:
    global _PROVIDER
    _PROVIDER = provider
    logger.info(
        "Retrieval provider set to %s",
        getattr(provider, "name", type(provider).__name__),
    )


def get_retrieval_provider() -> RetrievalProvider:
    return _PROVIDER


def clear_retrieval_provider() -> None:
    global _PROVIDER
    _PROVIDER = NoOpRetrieval()
    _CORPUS_PROVIDERS.clear()


def resolve_retrieval_name(raw: str | None = None) -> str:
    """Normalize ``EDIM_RETRIEVAL`` → none|memory|faiss|azure_ai_search|databricks_vector."""
    if raw is None:
        value = os.environ.get("EDIM_RETRIEVAL", "").strip().lower()
    else:
        value = raw.strip().lower()
    if not value or value in {"none", "off", "noop", "disabled"}:
        return "none"
    if value in {"memory", "mem", "inmemory"}:
        return "memory"
    if value in {"faiss", "local"}:
        return "faiss"
    if value in {"azure_ai_search", "azure", "azure_search", "ai_search"}:
        return "azure_ai_search"
    if value in {"databricks_vector", "databricks", "dbx_vector", "vector_search"}:
        return "databricks_vector"
    raise ValueError(
        f"Unknown EDIM_RETRIEVAL={value!r}; expected "
        "none|memory|faiss|azure_ai_search|databricks_vector"
    )


def create_retrieval_provider(name: str | None = None, **kwargs: Any) -> RetrievalProvider:
    resolved = resolve_retrieval_name(name)
    if resolved == "none":
        return NoOpRetrieval()
    if resolved == "memory":
        return MemoryRetrieval()
    if resolved == "faiss":
        from edim_dde_ai.retrieval.faiss_provider import FaissRetrieval

        return FaissRetrieval(**kwargs)
    if resolved == "azure_ai_search":
        from edim_dde_ai.retrieval.azure_provider import AzureAISearchRetrieval

        return AzureAISearchRetrieval(**kwargs)
    if resolved == "databricks_vector":
        from edim_dde_ai.retrieval.databricks_provider import DatabricksVectorRetrieval

        return DatabricksVectorRetrieval(**kwargs)
    raise ValueError(f"Unknown retrieval backend {resolved!r}")


def configure_retrieval_from_env(**kwargs: Any) -> RetrievalProvider:
    """Create provider from ``EDIM_RETRIEVAL`` and install it."""
    provider = create_retrieval_provider(None, **kwargs)
    set_retrieval_provider(provider)
    return provider


def provider_for_corpus(corpus: str) -> RetrievalProvider:
    """Resolve provider for a corpus (optional per-corpus override)."""
    cfg = get_corpus(corpus)
    if cfg and cfg.provider:
        if corpus in _CORPUS_PROVIDERS:
            return _CORPUS_PROVIDERS[corpus]
        kwargs: dict[str, Any] = {}
        name = resolve_retrieval_name(cfg.provider)
        if name == "faiss" and cfg.index_path:
            kwargs["index_dir"] = cfg.index_path
        if name == "azure_ai_search" and cfg.azure_index:
            kwargs["corpus_indexes"] = {corpus: cfg.azure_index}
            kwargs.setdefault("default_index", cfg.azure_index)
        if name == "databricks_vector" and cfg.databricks_index:
            kwargs["corpus_indexes"] = {corpus: cfg.databricks_index}
            kwargs.setdefault("default_index", cfg.databricks_index)
        provider = create_retrieval_provider(name, **kwargs)
        _CORPUS_PROVIDERS[corpus] = provider
        return provider
    return get_retrieval_provider()


def search_corpus(
    query: str,
    *,
    corpus: str = "default",
    top_k: int = 5,
    search_mode: str = "hybrid",
    filters: dict[str, Any] | None = None,
    dedupe: bool = True,
) -> list[RetrievalHit]:
    """Convenience search using corpus-aware provider resolution.

    When ``dedupe`` is true (default), drops duplicate ``id`` then duplicate
    action signatures / content hashes so prompts do not repeat the same
    guidance or past action.
    """
    provider = provider_for_corpus(corpus)
    # Over-fetch slightly so de-dupe can still fill top_k
    fetch_k = max(1, int(top_k))
    if dedupe:
        fetch_k = min(max(fetch_k * 3, fetch_k + 5), 50)
    hits = provider.search(
        SearchRequest(
            query=query,
            corpus=corpus,
            top_k=fetch_k,
            search_mode=search_mode,
            filters=dict(filters or {}),
        )
    )
    if dedupe:
        from edim_dde_ai.experiences.dedupe import dedupe_retrieval_hits

        hits = dedupe_retrieval_hits(hits)
    return hits[: max(1, int(top_k))]


__all__ = [
    "set_retrieval_provider",
    "get_retrieval_provider",
    "clear_retrieval_provider",
    "resolve_retrieval_name",
    "create_retrieval_provider",
    "configure_retrieval_from_env",
    "provider_for_corpus",
    "search_corpus",
    "format_hits_as_context",
]
