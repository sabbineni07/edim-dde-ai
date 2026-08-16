"""Process-wide retrieval provider registry and environment factory.

Business purpose
----------------
One default provider per process (same pattern as StateStore / WebSearch).
API lifespan typically calls ``configure_retrieval_from_env()``; tests call
``set_retrieval_provider(MemoryRetrieval())``. Per-corpus overrides from
``CorpusConfig.provider`` are cached in ``_CORPUS_PROVIDERS``.

Public API
----------
* ``set_retrieval_provider`` / ``get_retrieval_provider`` / ``clear_retrieval_provider``
* ``resolve_retrieval_name`` / ``create_retrieval_provider`` /
  ``configure_retrieval_from_env``
* ``provider_for_corpus`` / ``search_corpus``

Env
---
* ``EDIM_RETRIEVAL`` — ``none`` | ``memory`` | ``faiss`` | ``azure_ai_search`` |
  ``databricks_vector`` (aliases accepted; see ``resolve_retrieval_name``)
"""

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
    """Replace the process-wide default provider (tests / custom host wiring).

    Args:
        provider: Any object satisfying ``RetrievalProvider``.
    """
    global _PROVIDER
    _PROVIDER = provider
    logger.info(
        "Retrieval provider set to %s",
        getattr(provider, "name", type(provider).__name__),
    )


def get_retrieval_provider() -> RetrievalProvider:
    """Return the current process-wide default provider (never ``None``).

    Returns:
        The installed ``RetrievalProvider`` (defaults to ``NoOpRetrieval``).
    """
    return _PROVIDER


def clear_retrieval_provider() -> None:
    """Reset to ``NoOpRetrieval`` and drop per-corpus provider cache."""
    global _PROVIDER
    _PROVIDER = NoOpRetrieval()
    _CORPUS_PROVIDERS.clear()


def resolve_retrieval_name(raw: str | None = None) -> str:
    """Normalize a backend name (or ``EDIM_RETRIEVAL``) to a canonical id.

    Args:
        raw: Explicit name, or ``None`` to read ``EDIM_RETRIEVAL``.

    Returns:
        One of ``none`` | ``memory`` | ``faiss`` | ``azure_ai_search`` |
        ``databricks_vector``.

    Raises:
        ValueError: Unknown backend alias.
    """
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
    """Factory for built-in backends (does not install into the process registry).

    Args:
        name: Backend name or alias; ``None`` uses ``EDIM_RETRIEVAL``.
        **kwargs: Forwarded to the concrete constructor (e.g. ``index_dir``,
            ``corpus_indexes``).

    Returns:
        A new ``RetrievalProvider`` instance.

    Raises:
        ValueError: Unknown resolved backend name.
        RuntimeError: Missing optional deps or required env (from constructors).
    """
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
    """Create provider from ``EDIM_RETRIEVAL`` and install it as the process default.

    Args:
        **kwargs: Forwarded to ``create_retrieval_provider``.

    Returns:
        The provider that was installed (also via ``get_retrieval_provider``).
    """
    provider = create_retrieval_provider(None, **kwargs)
    set_retrieval_provider(provider)
    return provider


def provider_for_corpus(corpus: str) -> RetrievalProvider:
    """Resolve the provider for a logical corpus (optional per-corpus override).

    When ``CorpusConfig.provider`` is set, builds (and caches) a dedicated
    provider with index path / Azure / Databricks overrides from the corpus
    config. Otherwise returns the process-wide default.

    Args:
        corpus: Logical corpus name registered via ``register_corpus`` / YAML.

    Returns:
        A ``RetrievalProvider`` suitable for searching that corpus.
    """
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
    status_boost: bool = True,
) -> list[RetrievalHit]:
    """Convenience search using corpus-aware provider resolution.

    Pipeline: provider search → optional metadata post-filter → optional
    de-dupe → optional status boost → truncate to ``top_k``.

    When ``dedupe`` is true (default), drops duplicate ``id`` then duplicate
    action signatures / content hashes so prompts do not repeat the same
    guidance or past action.

    When ``status_boost`` is true (default), adds a small score nudge for
    ``applied`` / ``accepted`` experience hits (no-op when metadata has no
    status — e.g. runbooks).

    Args:
        query: Search text.
        corpus: Logical corpus name.
        top_k: Maximum hits to return after optional de-dupe / boost.
        search_mode: ``vector`` | ``keyword`` | ``hybrid``.
        filters: Optional metadata equality filters (post-filter; works for
            all backends). Prefer over-fetch via ``dedupe`` when filtering.
        dedupe: When true, over-fetch then run ``dedupe_retrieval_hits``.
        status_boost: When true, prefer accepted/applied outcomes in ranking.

    Returns:
        Up to ``top_k`` ranked ``RetrievalHit`` rows.

    Example::

        hits = search_corpus("OOM executor", corpus="spark-runbooks", top_k=5)
        ctx = format_hits_as_context(hits)
    """
    provider = provider_for_corpus(corpus)
    # Over-fetch slightly so de-dupe / filters can still fill top_k
    fetch_k = max(1, int(top_k))
    if dedupe or filters:
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
    if filters:
        from edim_dde_ai.experiences.entity import filter_hits_by_metadata

        hits = filter_hits_by_metadata(hits, filters)
    if dedupe:
        from edim_dde_ai.experiences.dedupe import dedupe_retrieval_hits

        hits = dedupe_retrieval_hits(hits)
    if status_boost:
        from edim_dde_ai.experiences.ranking import apply_status_boost

        hits = apply_status_boost(hits)
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
