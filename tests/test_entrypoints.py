import json
from pathlib import Path

import pytest

from edim_dde_ai import (
    create_agent,
    get_agent_definition,
    list_agents,
    register_from_dict,
    register_from_dicts,
    register_from_directory,
    register_from_json,
    register_from_paths,
    register_from_yaml,
)
from edim_dde_ai.errors import DefinitionError, FoundationError

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"

ECHO_DICT = {
    "agent_id": "echo_agent",
    "display_name": "Echo Agent",
    "version": 1,
    "entry": {"method": "invoke", "sync": True},
    "graph": {
        "entry": "greet",
        "nodes": [
            {
                "id": "greet",
                "type": "set_value",
                "field": "greeting",
                "value": "hello",
            },
            {
                "id": "finish",
                "type": "echo_result",
                "from_fields": ["greeting", "message"],
            },
        ],
        "edges": [["greet", "finish"], ["finish", "END"]],
    },
}


def test_register_from_yaml():
    aid = register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    assert aid == "echo_agent"
    assert "echo_agent" in list_agents()
    defn = get_agent_definition("echo_agent")
    assert defn.display_name == "Echo Agent"


def test_register_from_directory():
    ids = register_from_directory(EXAMPLES)
    assert "echo_agent" in ids
    assert "two_step_agent" in ids
    agent = create_agent("two_step_agent")
    assert agent.invoke({"message": "z"})["result"]["message"] == "z"


def test_register_from_paths():
    ids = register_from_paths([EXAMPLES / "echo_agent.agent.yaml"])
    assert ids == ["echo_agent"]


def test_register_from_dict_invoke():
    aid = register_from_dict(ECHO_DICT)
    assert aid == "echo_agent"
    agent = create_agent("echo_agent")
    out = agent.invoke({"message": "hi"})
    assert out["result"]["greeting"] == "hello"
    assert out["result"]["message"] == "hi"


def test_register_from_json_invoke():
    aid = register_from_json(json.dumps(ECHO_DICT))
    assert aid == "echo_agent"
    agent = create_agent("echo_agent")
    out = agent.invoke({"message": "hi"})
    assert out["result"]["greeting"] == "hello"
    assert out["result"]["message"] == "hi"


def test_register_from_json_invalid_raises():
    with pytest.raises(DefinitionError) as excinfo:
        register_from_json("{not-json")
    assert issubclass(type(excinfo.value), FoundationError)
    assert "Invalid JSON" in str(excinfo.value)


def test_register_from_json_non_object_raises():
    with pytest.raises(DefinitionError):
        register_from_json(json.dumps(["not", "a", "dict"]))


def test_register_from_dict_missing_agent_id():
    bad = {k: v for k, v in ECHO_DICT.items() if k != "agent_id"}
    with pytest.raises(DefinitionError) as excinfo:
        register_from_dict(bad)
    assert "agent_id" in str(excinfo.value)


def test_register_from_dicts():
    other = dict(ECHO_DICT)
    other["agent_id"] = "echo_agent_2"
    other["display_name"] = "Echo Agent 2"
    ids = register_from_dicts([ECHO_DICT, other])
    assert ids == ["echo_agent", "echo_agent_2"]
