"""Pluggable observability provider tests."""

from __future__ import annotations

import pytest

from edim_dde_ai.observability import (
    LangSmithObservability,
    NoOpObservability,
    clear_observability_provider,
    configure_observability_from_env,
    create_observability_provider,
    get_observability_provider,
    resolve_observability_name,
    set_observability_provider,
)


def test_resolve_auto_none(monkeypatch):
    monkeypatch.delenv("EDIM_OBSERVABILITY", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("EDIM_LANGSMITH_ENABLED", raising=False)
    assert resolve_observability_name("auto") == "none"
    assert resolve_observability_name(None) == "none"


def test_resolve_auto_langsmith(monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.delenv("EDIM_LANGSMITH_ENABLED", raising=False)
    assert resolve_observability_name("auto") == "langsmith"


def test_create_and_set_langsmith(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    p = create_observability_provider("langsmith")
    assert isinstance(p, LangSmithObservability)
    assert p.name == "langsmith"
    set_observability_provider(p)
    assert get_observability_provider().name == "langsmith"
    out = p.merge_invoke_kwargs("demo", {}, request_id="abc")
    assert out["config"]["metadata"]["request_id"] == "abc"
    assert out["config"]["metadata"]["observability"] == "langsmith"
    assert "obs:langsmith" in out["config"]["tags"]


def test_noop_provider():
    p = create_observability_provider("none")
    assert isinstance(p, NoOpObservability)
    out = p.merge_invoke_kwargs("demo", {}, request_id="r1")
    assert out["config"]["metadata"]["request_id"] == "r1"


def test_mlflow_provider_factory():
    try:
        p = create_observability_provider("mlflow")
    except RuntimeError as exc:
        assert "mlflow" in str(exc).lower()
        return
    assert p.name == "mlflow"
    out = p.merge_invoke_kwargs("demo", {}, request_id="m1")
    assert out["config"]["metadata"]["observability"] == "mlflow"


def test_configure_from_env(monkeypatch):
    monkeypatch.setenv("EDIM_OBSERVABILITY", "langsmith")
    p = configure_observability_from_env()
    assert p.name == "langsmith"
    assert get_observability_provider().name == "langsmith"
    clear_observability_provider()
    assert get_observability_provider().name == "none"


def test_unknown_backend():
    with pytest.raises(ValueError, match="Unknown"):
        resolve_observability_name("datadog")
