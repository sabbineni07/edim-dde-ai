"""Pluggable retrieval / similarity search (FAISS · Azure AI Search · Databricks)."""

from edim_dde_ai.retrieval.corpus import (
    CorpusConfig,
    clear_corpora,
    get_corpus,
    list_corpora,
    load_corpora_yaml,
    register_corpus,
)
from edim_dde_ai.retrieval.memory import MemoryRetrieval
from edim_dde_ai.retrieval.models import (
    RetrievalHit,
    SearchRequest,
    format_hits_as_context,
)
from edim_dde_ai.retrieval.noop import NoOpRetrieval
from edim_dde_ai.retrieval.protocols import RetrievalProvider
from edim_dde_ai.retrieval.registry import (
    clear_retrieval_provider,
    configure_retrieval_from_env,
    create_retrieval_provider,
    get_retrieval_provider,
    provider_for_corpus,
    resolve_retrieval_name,
    search_corpus,
    set_retrieval_provider,
)

__all__ = [
    "RetrievalProvider",
    "RetrievalHit",
    "SearchRequest",
    "format_hits_as_context",
    "NoOpRetrieval",
    "MemoryRetrieval",
    "CorpusConfig",
    "register_corpus",
    "get_corpus",
    "list_corpora",
    "clear_corpora",
    "load_corpora_yaml",
    "set_retrieval_provider",
    "get_retrieval_provider",
    "clear_retrieval_provider",
    "create_retrieval_provider",
    "configure_retrieval_from_env",
    "resolve_retrieval_name",
    "provider_for_corpus",
    "search_corpus",
]


def __getattr__(name: str):
    if name == "FaissRetrieval":
        from edim_dde_ai.retrieval.faiss_provider import FaissRetrieval

        return FaissRetrieval
    if name == "AzureAISearchRetrieval":
        from edim_dde_ai.retrieval.azure_provider import AzureAISearchRetrieval

        return AzureAISearchRetrieval
    if name == "DatabricksVectorRetrieval":
        from edim_dde_ai.retrieval.databricks_provider import DatabricksVectorRetrieval

        return DatabricksVectorRetrieval
    if name == "build_faiss_index_from_dir":
        from edim_dde_ai.retrieval.faiss_provider import build_faiss_index_from_dir

        return build_faiss_index_from_dir
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
