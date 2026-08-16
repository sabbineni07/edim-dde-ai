"""Agent ``bindings.llm`` parse / resolve / GraphBuilder injection."""

from __future__ import annotations

from pathlib import Path

import pytest

from edim_dde_ai import create_agent, register_from_yaml
from edim_dde_ai.core.bindings import (
    AgentBindings,
    LlmBinding,
    parse_agent_bindings,
    resolve_llm_binding,
)
from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.core.env_refs import EnvRefError
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.registry.chains import register_chain_invoker


def _minimal(**overrides):
    data = {
        "agent_id": "demo",
        "graph": {
            "entry": "a",
            "nodes": [{"id": "a", "type": "passthrough"}],
            "edges": [["a", "END"]],
        },
    }
    data.update(overrides)
    return data


def test_parse_omitted_bindings():
    assert parse_agent_bindings(_minimal()) is None
    defn = parse_agent_definition(_minimal())
    assert defn.bindings is None


def test_parse_llm_bindings():
    data = _minimal(
        bindings={
            "llm": {
                "endpoint": "${ENV:EDIM_FOUNDRY_ENDPOINT_RCA}",
                "deployment": "${ENV:EDIM_FOUNDRY_DEPLOYMENT_RCA}",
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 40,
                "max_tokens": 4096,
            }
        }
    )
    bindings = parse_agent_bindings(data)
    assert isinstance(bindings, AgentBindings)
    assert bindings.llm == LlmBinding(
        endpoint="${ENV:EDIM_FOUNDRY_ENDPOINT_RCA}",
        deployment="${ENV:EDIM_FOUNDRY_DEPLOYMENT_RCA}",
        temperature=0.0,
        top_p=1.0,
        top_k=40,
        max_tokens=4096,
    )


def test_parse_partial_llm_binding():
    bindings = parse_agent_bindings(
        _minimal(bindings={"llm": {"deployment": "gpt-rca-only"}})
    )
    assert bindings is not None
    assert bindings.llm is not None
    assert bindings.llm.endpoint is None
    assert bindings.llm.deployment == "gpt-rca-only"


def test_parse_llm_rejects_bad_temperature():
    with pytest.raises(DefinitionError, match="bindings.llm.temperature"):
        parse_agent_bindings(_minimal(bindings={"llm": {"temperature": 9}}))


def test_parse_search_cosmos_sql_warehouse_bindings():
    from edim_dde_ai.core.bindings import (
        CosmosBinding,
        SearchBinding,
        SqlWarehouseBinding,
    )

    bindings = parse_agent_bindings(
        _minimal(
            bindings={
                "llm": {
                    "endpoint": "${ENV:AZURE_OPENAI_ENDPOINT}",
                    "deployment": "${ENV:AZURE_OPENAI_DEPLOYMENT_NAME}",
                },
                "search": {
                    "endpoint": "${ENV:EDIM_AZURE_SEARCH_ENDPOINT}",
                    "index": "${ENV:EDIM_AZURE_SEARCH_INDEX}",
                },
                "cosmos": {
                    "endpoint": "${ENV:EDIM_COSMOS_ENDPOINT}",
                    "database": "${ENV:EDIM_COSMOS_DATABASE}",
                },
                "sql-warehouse": {
                    "host": "${ENV:DATABRICKS_HOST}",
                    "http_path": "${ENV:DATABRICKS_HTTP_PATH}",
                },
            }
        )
    )
    assert bindings is not None
    assert bindings.search == SearchBinding(
        endpoint="${ENV:EDIM_AZURE_SEARCH_ENDPOINT}",
        index="${ENV:EDIM_AZURE_SEARCH_INDEX}",
    )
    assert bindings.cosmos == CosmosBinding(
        endpoint="${ENV:EDIM_COSMOS_ENDPOINT}",
        database="${ENV:EDIM_COSMOS_DATABASE}",
    )
    assert bindings.sql_warehouse == SqlWarehouseBinding(
        host="${ENV:DATABRICKS_HOST}",
        http_path="${ENV:DATABRICKS_HTTP_PATH}",
    )


def test_parse_bindings_bad_shape():
    with pytest.raises(DefinitionError, match="bindings must be a mapping"):
        parse_agent_bindings(_minimal(bindings="nope"))
    with pytest.raises(DefinitionError, match="bindings.llm must be a mapping"):
        parse_agent_bindings(_minimal(bindings={"llm": "nope"}))
    with pytest.raises(DefinitionError, match="bindings.search must be a mapping"):
        parse_agent_bindings(_minimal(bindings={"search": "nope"}))
    with pytest.raises(DefinitionError, match="bindings.cosmos.database"):
        parse_agent_bindings(
            _minimal(bindings={"cosmos": {"database": "  "}})
        )
    with pytest.raises(DefinitionError, match="bindings.sql-warehouse"):
        parse_agent_bindings(_minimal(bindings={"sql-warehouse": "nope"}))


def test_resolve_llm_binding_globals_when_omitted():
    resolved = resolve_llm_binding(None)
    assert resolved.endpoint is None
    assert resolved.deployment is None
    assert resolved.temperature is None


def test_resolve_llm_binding_env():
    bindings = AgentBindings(
        llm=LlmBinding(
            endpoint="${ENV:E}",
            deployment="${ENV:D}",
            temperature=0.1,
            top_p=0.9,
            top_k=20,
            max_tokens=1024,
        )
    )
    resolved = resolve_llm_binding(
        bindings, environ={"E": "https://e.example", "D": "dep"}
    )
    assert resolved.endpoint == "https://e.example"
    assert resolved.deployment == "dep"
    assert resolved.temperature == 0.1
    assert resolved.top_p == 0.9
    assert resolved.top_k == 20
    assert resolved.max_tokens == 1024


def test_resolve_llm_binding_fail_closed():
    bindings = AgentBindings(
        llm=LlmBinding(endpoint="${ENV:MISSING}", deployment=None)
    )
    with pytest.raises(EnvRefError):
        resolve_llm_binding(bindings, environ={})


def test_graph_builder_injects_llm_bindings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EDIM_FOUNDRY_ENDPOINT_RCA", "https://rca.example.com")
    monkeypatch.setenv("EDIM_FOUNDRY_DEPLOYMENT_RCA", "gpt-rca")

    captured: dict = {}

    @register_chain_invoker("capture_bindings_cfg")
    def _capture(state, config):
        captured.clear()
        captured.update(config)
        return "ok"

    yaml_text = """
agent_id: bindings_llm_demo
bindings:
  llm:
    endpoint: ${ENV:EDIM_FOUNDRY_ENDPOINT_RCA}
    deployment: ${ENV:EDIM_FOUNDRY_DEPLOYMENT_RCA}
    temperature: 0.0
    top_p: 1.0
    top_k: 40
    max_tokens: 4096
graph:
  entry: call
  nodes:
    - id: call
      type: llm_chain
      chain: capture_bindings_cfg
      output_key: llm_raw
  edges:
    - [call, END]
"""
    path = tmp_path / "bindings.agent.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    register_from_yaml(path)
    out = create_agent("bindings_llm_demo").invoke({})
    assert out["llm_raw"] == "ok"
    assert captured.get("endpoint") == "https://rca.example.com"
    assert captured.get("deployment") == "gpt-rca"
    assert captured.get("temperature") == 0.0
    assert captured.get("top_p") == 1.0
    assert captured.get("top_k") == 40
    assert captured.get("max_tokens") == 4096
    assert captured.get("agent_id") == "bindings_llm_demo"


def test_graph_builder_no_injection_without_bindings(tmp_path: Path):
    captured: dict = {}

    @register_chain_invoker("capture_no_bindings_cfg")
    def _capture(state, config):
        captured.clear()
        captured.update(config)
        return "ok"

    yaml_text = """
agent_id: no_bindings_llm_demo
graph:
  entry: call
  nodes:
    - id: call
      type: llm_chain
      chain: capture_no_bindings_cfg
      output_key: llm_raw
  edges:
    - [call, END]
"""
    path = tmp_path / "no_bindings.agent.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    register_from_yaml(path)
    create_agent("no_bindings_llm_demo").invoke({})
    assert "endpoint" not in captured
    assert "deployment" not in captured
    assert "temperature" not in captured
