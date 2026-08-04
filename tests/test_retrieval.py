"""Unit tests for pluggable retrieval providers and rag.retrieve node."""

from __future__ import annotations

from edim_dde_ai import register_from_dict, create_agent
from edim_dde_ai.retrieval import (
    MemoryRetrieval,
    configure_retrieval_from_env,
    create_retrieval_provider,
    format_hits_as_context,
    get_retrieval_provider,
    resolve_retrieval_name,
    search_corpus,
    set_retrieval_provider,
)
from edim_dde_ai.retrieval.models import RetrievalHit, SearchRequest


def test_resolve_retrieval_names():
    assert resolve_retrieval_name("faiss") == "faiss"
    assert resolve_retrieval_name("azure") == "azure_ai_search"
    assert resolve_retrieval_name("databricks") == "databricks_vector"
    assert resolve_retrieval_name("") == "none"


def test_memory_search_and_format():
    store = MemoryRetrieval()
    store.upsert(
        corpus="spark-runbooks",
        doc_id="oom",
        text="Executor OutOfMemoryError: increase spark.executor.memoryOverhead",
        source="oom.md",
    )
    store.upsert(
        corpus="spark-runbooks",
        doc_id="skew",
        text="Data skew on shuffle join — salting keys helps",
        source="skew.md",
    )
    set_retrieval_provider(store)
    hits = search_corpus(
        "OutOfMemoryError executor memory",
        corpus="spark-runbooks",
        top_k=2,
    )
    assert hits
    assert hits[0].id == "oom"
    ctx = format_hits_as_context(hits)
    assert "OutOfMemoryError" in ctx


def test_configure_none_from_env(monkeypatch):
    monkeypatch.setenv("EDIM_RETRIEVAL", "none")
    p = configure_retrieval_from_env()
    assert p.name == "none"
    assert get_retrieval_provider().search(
        SearchRequest(query="x", corpus="c")
    ) == []


def test_rag_retrieve_node_in_graph():
    store = MemoryRetrieval()
    store.upsert(
        corpus="spark-runbooks",
        doc_id="oom",
        text="OOM runbook: raise executor memory",
        source="oom.md",
    )
    set_retrieval_provider(store)

    register_from_dict(
        {
            "agent_id": "ret_demo",
            "graph": {
                "entry": "retrieve",
                "nodes": [
                    {
                        "id": "retrieve",
                        "type": "rag.retrieve",
                        "corpus": "spark-runbooks",
                        "top_k": 3,
                        "query_key": "retrieval_query",
                        "output_key": "runbook_hits",
                        "context_key": "runbook_context",
                    }
                ],
                "edges": [["START", "retrieve"], ["retrieve", "END"]],
            },
        }
    )
    out = create_agent("ret_demo").invoke(
        {"retrieval_query": "executor OOM memory"}
    )
    assert out.get("runbook_hits")
    assert "OOM" in (out.get("runbook_context") or "")


def test_create_memory_provider():
    p = create_retrieval_provider("memory")
    assert p.name == "memory"
    p.upsert(corpus="c", doc_id="1", text="hello world")
    hits = p.search(SearchRequest(query="hello", corpus="c", top_k=1))
    assert len(hits) == 1
    assert isinstance(hits[0], RetrievalHit)
