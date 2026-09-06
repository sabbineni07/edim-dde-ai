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


def test_invoke_agent_shared_state_native_subgraph():
    """No I/O map → child attached via add_node(compiled) (shared AgentState)."""
    register_from_dict(
        {
            "agent_id": "sg_child",
            "graph": {
                "nodes": [
                    {
                        "id": "greet",
                        "type": "set_value",
                        "field": "greeting",
                        "template": "hi-{name}",
                    }
                ],
                "edges": [["START", "greet"], ["greet", "END"]],
            },
        }
    )
    register_from_dict(
        {
            "agent_id": "sg_parent",
            "graph": {
                "nodes": [
                    {"id": "seed", "type": "set_value", "field": "name", "value": "ada"},
                    {
                        "id": "call_child",
                        "type": "invoke_agent",
                        "agent_id": "sg_child",
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
    out = create_agent("sg_parent").invoke({})
    assert out.get("name") == "ada"
    assert out.get("greeting") == "hi-ada"


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
        create_agent("selfish")


def test_invoke_agent_native_shared_state_example_yaml():
    """examples/agents native parent embeds child via shared AgentState."""
    from pathlib import Path

    from edim_dde_ai.api.entrypoints import register_from_yaml

    root = Path(__file__).resolve().parents[1] / "examples" / "agents"
    register_from_yaml(root / "invoke_agent_child.agent.yaml")
    register_from_yaml(root / "invoke_agent_native_parent.agent.yaml")
    out = create_agent("invoke_native_parent_demo").invoke({})
    assert out.get("name") == "ada"
    assert out.get("greeting") == "hello-ada"


def test_invoke_agent_cycle_rejected():
    register_from_dict(
        {
            "agent_id": "cyc_a",
            "graph": {
                "nodes": [
                    {
                        "id": "to_b",
                        "type": "invoke_agent",
                        "agent_id": "cyc_b",
                    }
                ],
                "edges": [["START", "to_b"], ["to_b", "END"]],
            },
        }
    )
    register_from_dict(
        {
            "agent_id": "cyc_b",
            "graph": {
                "nodes": [
                    {
                        "id": "to_a",
                        "type": "invoke_agent",
                        "agent_id": "cyc_a",
                    }
                ],
                "edges": [["START", "to_a"], ["to_a", "END"]],
            },
        }
    )
    with pytest.raises(DefinitionError, match="cycle"):
        create_agent("cyc_a")


def test_langsmith_config_tags(monkeypatch):
    monkeypatch.setenv("EDIM_ENV", "dev")
    cfg = build_run_config(agent_id="cluster_tuning", request_id="r-1")
    assert "agent_id:cluster_tuning" in cfg["tags"]
    assert "env:dev" in cfg["tags"]
    assert cfg["metadata"]["request_id"] == "r-1"
    merged = merge_invoke_kwargs("cluster_tuning", {}, request_id="r-2")
    assert merged["config"]["metadata"]["request_id"] == "r-2"
