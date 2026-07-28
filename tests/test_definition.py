import pytest

from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.errors import DefinitionError


def _minimal(**overrides):
    data = {
        "agent_id": "demo",
        "display_name": "Demo",
        "version": 1,
        "graph": {
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "passthrough"},
                {"id": "b", "type": "passthrough"},
            ],
            "edges": [["a", "b"], ["b", "END"]],
        },
    }
    data.update(overrides)
    return data


def test_parse_ok():
    defn = parse_agent_definition(_minimal())
    assert defn.agent_id == "demo"
    assert defn.graph_entry == "a"
    assert len(defn.nodes) == 2
    assert defn.edges[-1] == ("b", "END")


def test_missing_agent_id():
    data = _minimal()
    del data["agent_id"]
    with pytest.raises(DefinitionError, match="agent_id"):
        parse_agent_definition(data)


def test_unknown_entry_node():
    data = _minimal()
    data["graph"]["entry"] = "missing"
    with pytest.raises(DefinitionError, match="graph.entry"):
        parse_agent_definition(data)


def test_duplicate_node_id():
    data = _minimal()
    data["graph"]["nodes"].append({"id": "a", "type": "passthrough"})
    with pytest.raises(DefinitionError, match="Duplicate"):
        parse_agent_definition(data)


def test_conditional_edges():
    data = _minimal()
    data["graph"]["conditional_edges"] = [
        {
            "source": "a",
            "router": "field_truthy",
            "config": {"field": "flag"},
            "mapping": {"yes": "b", "no": "END"},
        }
    ]
    # remove normal edge from a so definition still valid
    data["graph"]["edges"] = [["b", "END"]]
    defn = parse_agent_definition(data)
    assert len(defn.conditional_edges) == 1
    assert defn.conditional_edges[0].router == "field_truthy"
    assert defn.conditional_edges[0].config == {"field": "flag"}


def test_conditional_edges_reject_from_key():
    data = _minimal()
    data["graph"]["conditional_edges"] = [
        {
            "from": "a",
            "router": "field_truthy",
            "config": {"field": "flag"},
            "mapping": {"yes": "b", "no": "END"},
        }
    ]
    data["graph"]["edges"] = [["b", "END"]]
    with pytest.raises(DefinitionError, match="use 'source'"):
        parse_agent_definition(data)


def test_start_edge_derives_entry():
    data = _minimal()
    del data["graph"]["entry"]
    data["graph"]["edges"] = [["START", "a"], ["a", "b"], ["b", "END"]]
    defn = parse_agent_definition(data)
    assert defn.graph_entry == "a"
    assert defn.edges[0] == ("START", "a")


def test_start_edge_matches_explicit_entry():
    data = _minimal()
    data["graph"]["edges"] = [["START", "a"], ["a", "b"], ["b", "END"]]
    defn = parse_agent_definition(data)
    assert defn.graph_entry == "a"


def test_start_edge_conflicts_with_entry():
    data = _minimal()
    data["graph"]["entry"] = "b"
    data["graph"]["edges"] = [["START", "a"], ["a", "b"], ["b", "END"]]
    with pytest.raises(DefinitionError, match="conflicts with START"):
        parse_agent_definition(data)


def test_multiple_start_targets_rejected():
    data = _minimal()
    del data["graph"]["entry"]
    data["graph"]["edges"] = [["START", "a"], ["START", "b"], ["b", "END"]]
    with pytest.raises(DefinitionError, match="multiple distinct START"):
        parse_agent_definition(data)


def test_missing_entry_and_start_rejected():
    data = _minimal()
    del data["graph"]["entry"]
    with pytest.raises(DefinitionError, match="graph requires entry"):
        parse_agent_definition(data)


def test_reserved_node_id_rejected():
    data = _minimal()
    data["graph"]["nodes"].append({"id": "END", "type": "passthrough"})
    with pytest.raises(DefinitionError, match="reserved"):
        parse_agent_definition(data)
