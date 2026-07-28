"""Tests for richer routers and graph.routes sugar."""

from __future__ import annotations

import pytest

from edim_dde_ai import create_agent, register_from_dict
from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.errors import DefinitionError, RouterRegistryError
from edim_dde_ai.registry.routers import clear_routers, get_router, list_routers


@pytest.fixture(autouse=True)
def _reset_routers():
    clear_routers(keep_builtins=True)
    yield
    clear_routers(keep_builtins=True)


def test_builtin_router_names():
    names = set(list_routers())
    assert {
        "field_truthy",
        "field_equals",
        "field_in",
        "field_compare",
        "choice",
    } <= names


def test_field_equals():
    route = get_router("field_equals")({"field": "cat", "value": "oom"})
    assert route({"cat": "oom"}) == "yes"
    assert route({"cat": "timeout"}) == "no"


def test_field_in():
    route = get_router("field_in")({"field": "status", "values": ["a", "b"]})
    assert route({"status": "a"}) == "yes"
    assert route({"status": "z"}) == "no"


def test_field_compare():
    route = get_router("field_compare")({"field": "n", "op": "gt", "value": 10})
    assert route({"n": 11}) == "yes"
    assert route({"n": 5}) == "no"


def test_field_compare_type_error_is_false():
    route = get_router("field_compare")({"field": "n", "op": "gt", "value": 10})
    assert route({"n": "x"}) == "no"


def test_choice():
    route = get_router("choice")({"field": "cat", "default": "default"})
    assert route({"cat": "oom"}) == "oom"
    assert route({}) == "default"
    assert route({"cat": None}) == "default"


def test_field_equals_requires_value():
    with pytest.raises(RouterRegistryError, match="value"):
        get_router("field_equals")({"field": "x"})


def test_routes_sugar_truthy():
    data = {
        "agent_id": "sugar",
        "graph": {
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "passthrough"},
                {"id": "b", "type": "passthrough"},
            ],
            "edges": [["b", "END"]],
            "routes": [
                {
                    "after": "a",
                    "when": {"field": "flag", "op": "truthy"},
                    "then": "b",
                    "else": "END",
                }
            ],
        },
    }
    defn = parse_agent_definition(data)
    assert len(defn.conditional_edges) == 1
    cond = defn.conditional_edges[0]
    assert cond.source == "a"
    assert cond.router == "field_truthy"
    assert cond.config["field"] == "flag"
    assert cond.mapping == {"yes": "b", "no": "END"}


def test_routes_sugar_switch():
    data = {
        "agent_id": "sugar_switch",
        "graph": {
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "passthrough"},
                {"id": "oom", "type": "passthrough"},
                {"id": "other", "type": "passthrough"},
            ],
            "edges": [["oom", "END"], ["other", "END"]],
            "routes": [
                {
                    "after": "a",
                    "switch": "category",
                    "cases": {"oom": "oom"},
                    "else": "other",
                }
            ],
        },
    }
    defn = parse_agent_definition(data)
    cond = defn.conditional_edges[0]
    assert cond.router == "choice"
    assert cond.config == {"field": "category", "default": "default"}
    assert cond.mapping == {"oom": "oom", "default": "other"}


def test_routes_sugar_equals_and_compare():
    data = {
        "agent_id": "sugar_ops",
        "graph": {
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "passthrough"},
                {"id": "b", "type": "passthrough"},
                {"id": "c", "type": "passthrough"},
            ],
            "edges": [["b", "END"], ["c", "END"]],
            "routes": [
                {
                    "source": "a",
                    "when": {"field": "x", "op": "equals", "value": 1},
                    "then": "b",
                    "else": "c",
                }
            ],
        },
    }
    defn = parse_agent_definition(data)
    assert defn.conditional_edges[0].router == "field_equals"
    assert defn.conditional_edges[0].config["value"] == 1


def test_routes_reject_unknown_op():
    data = {
        "agent_id": "bad",
        "graph": {
            "entry": "a",
            "nodes": [{"id": "a", "type": "passthrough"}],
            "edges": [["a", "END"]],
            "routes": [
                {
                    "after": "a",
                    "when": {"field": "f", "op": "regex"},
                    "then": "END",
                    "else": "END",
                }
            ],
        },
    }
    with pytest.raises(DefinitionError, match="when.op"):
        parse_agent_definition(data)


def test_routes_sugar_end_to_end():
    register_from_dict(
        {
            "agent_id": "routes_e2e",
            "graph": {
                "entry": "decide",
                "nodes": [
                    {"id": "decide", "type": "passthrough"},
                    {
                        "id": "hi",
                        "type": "set_value",
                        "field": "msg",
                        "value": "hi",
                    },
                    {
                        "id": "lo",
                        "type": "set_value",
                        "field": "msg",
                        "value": "lo",
                    },
                ],
                "edges": [["hi", "END"], ["lo", "END"]],
                "routes": [
                    {
                        "after": "decide",
                        "when": {"field": "n", "op": "compare", "cmp": "gt", "value": 5},
                        "then": "hi",
                        "else": "lo",
                    }
                ],
            },
        },
        overwrite=True,
    )
    agent = create_agent("routes_e2e")
    assert agent.invoke({"n": 9})["msg"] == "hi"
    assert agent.invoke({"n": 1})["msg"] == "lo"
