"""Phase 0: extended schema blocks + invoke_agent + langsmith config helpers."""

from __future__ import annotations

import pytest

from edim_dde_ai.api.entrypoints import register_from_dict
from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.observability import build_run_config, merge_invoke_kwargs
from edim_dde_ai.registry.agents import create_agent
from edim_dde_ai.schema import validate_extended_blocks


def test_extended_metadata_ok():
    data = {
        "agent_id": "m",
        "metadata": {"risk_tier": "low", "lifecycle": "draft", "hitl_required": False},
        "graph": {
            "nodes": [{"id": "a", "type": "passthrough"}],
            "edges": [["START", "a"], ["a", "END"]],
        },
    }
    validate_extended_blocks(data)
    parse_agent_definition(data)


def test_extended_metadata_bad_risk():
    with pytest.raises(DefinitionError, match="risk_tier"):
        validate_extended_blocks(
            {
                "agent_id": "m",
                "metadata": {"risk_tier": "critical"},
                "graph": {"nodes": [{"id": "a", "type": "passthrough"}]},
            }
        )


def test_invoke_agent_spike():
    register_from_dict(
        {
            "agent_id": "invoke_child_demo",
            "graph": {
                "nodes": [
                    {
                        "id": "greet",
                        "type": "set_value",
                        "field": "greeting",
                        "template": "hello-{name}",
                    }
                ],
                "edges": [["START", "greet"], ["greet", "END"]],
            },
        }
    )
    register_from_dict(
        {
            "agent_id": "invoke_parent_demo",
            "graph": {
                "nodes": [
                    {"id": "seed", "type": "set_value", "field": "name", "value": "world"},
                    {
                        "id": "call_child",
                        "type": "invoke_agent",
                        "agent_id": "invoke_child_demo",
                        "input_keys": ["name"],
                        "output_map": {"greeting": "child_greeting"},
                    },
                ],
                "edges": [
                    ["START", "seed"],
                    ["seed", "call_child"],
                    ["call_child", "END"],
                ],
            },
        }
    )
    out = create_agent("invoke_parent_demo").invoke({})
    assert out.get("child_greeting") == "hello-world"
    assert out.get("name") == "world"


def test_invoke_agent_self_call_rejected():
    register_from_dict(
        {
            "agent_id": "selfish",
            "graph": {
                "nodes": [
                    {
                        "id": "loop",
                        "type": "invoke_agent",
                        "agent_id": "selfish",
                    }
                ],
                "edges": [["START", "loop"], ["loop", "END"]],
            },
        }
    )
    with pytest.raises(DefinitionError, match="self-call"):
        create_agent("selfish").invoke({})


def test_langsmith_config_tags(monkeypatch):
    monkeypatch.setenv("EDIM_ENV", "dev")
    cfg = build_run_config(agent_id="cluster_tuning", request_id="r-1")
    assert "agent_id:cluster_tuning" in cfg["tags"]
    assert "env:dev" in cfg["tags"]
    assert cfg["metadata"]["request_id"] == "r-1"
    merged = merge_invoke_kwargs("cluster_tuning", {}, request_id="r-2")
    assert merged["config"]["metadata"]["request_id"] == "r-2"
