from __future__ import annotations

from edim_dde_ai.nodes.builtin import web_search_factory
from edim_dde_ai.web import (
    MemoryWebSearch,
    NullWebSearch,
    WebSearchResult,
    set_web_search_provider,
)


def test_web_search_disabled_never_calls_provider():
    provider = MemoryWebSearch(
        [WebSearchResult(title="Doc", url="https://docs.databricks.com/x")]
    )
    set_web_search_provider(provider)
    try:
        out = web_search_factory({"enabled": False})(
            {"web_search_query": "private query"}
        )
        assert out["web_search_hits"] == []
        assert provider.requests == []
    finally:
        set_web_search_provider(NullWebSearch())


def test_web_search_returns_bounded_cited_context():
    provider = MemoryWebSearch(
        [
            WebSearchResult(
                title="Spark troubleshooting",
                url="https://spark.apache.org/docs/latest/tuning.html",
                snippet="Memory and serialization tuning guidance.",
            ),
            WebSearchResult(
                title="Untrusted",
                url="https://example.com/post",
                snippet="Not allowlisted.",
            ),
        ]
    )
    set_web_search_provider(provider)
    try:
        node = web_search_factory(
            {
                "enabled": True,
                "top_k": 3,
                "allowed_domains": ["spark.apache.org"],
            }
        )
        out = node({"web_search_query": "Spark memory failure"})
        assert len(out["web_search_hits"]) == 1
        assert "[web:1]" in out["web_search_context"]
        assert "https://spark.apache.org/" in out["web_search_context"]
        assert provider.requests[0].query == "Spark memory failure"
    finally:
        set_web_search_provider(NullWebSearch())


def test_web_search_without_provider_is_non_fatal():
    set_web_search_provider(NullWebSearch())
    out = web_search_factory({"enabled": True})(
        {"web_search_query": "Spark unknown failure"}
    )
    assert out["web_search_hits"] == []
    assert "no provider" in out["web_search_context"]
