"""Parse and validate agent definitions from dicts.

Turns a YAML/JSON agent mapping into a frozen ``AgentDefinition`` used by the
graph builder. Validation is structural only: node/router *ids* must exist in
Python registries at build time (no dynamic imports from YAML).

Conditional edges use the key ``source`` (not ``from``). Each item may include
optional ``config`` (a mapping) passed to the router factory.

Example::

    {
      "agent_id": "demo",
      "graph": {
        "entry": "a",
        "nodes": [{"id": "a", "type": "passthrough"}],
        "edges": [["a", "END"]],
        "conditional_edges": [
          {
            "source": "a",
            "router": "field_truthy",
            "config": {"field": "flag"},
            "mapping": {"yes": "END", "no": "END"},
          }
        ],
      },
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edim_dde_ai.errors import DefinitionError


@dataclass(frozen=True)
class EntrySpec:
    method: str = "invoke"
    sync: bool = True


@dataclass(frozen=True)
class NodeSpec:
    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConditionalEdgeSpec:
    """One conditional edge: ``source`` node, router name, config, label map.

    The standard key is ``source`` (not ``from``). ``config`` is passed to the
    registered router factory at graph-build time.
    """

    source: str
    router: str
    mapping: dict[str, str]
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    display_name: str
    version: int
    entry: EntrySpec
    graph_entry: str
    nodes: tuple[NodeSpec, ...]
    edges: tuple[tuple[str, str], ...]
    conditional_edges: tuple[ConditionalEdgeSpec, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}


def _require(data: dict[str, Any], key: str, path: str = "") -> Any:
    if key not in data:
        loc = f"{path}.{key}" if path else key
        raise DefinitionError(f"Missing required field: {loc}")
    return data[key]


def parse_agent_definition(data: dict[str, Any]) -> AgentDefinition:
    """Parse and validate an agent definition dict into AgentDefinition."""
    if not isinstance(data, dict):
        raise DefinitionError("Agent definition must be a mapping")

    agent_id = _require(data, "agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise DefinitionError("agent_id must be a non-empty string")

    display_name = data.get("display_name", agent_id)
    if not isinstance(display_name, str):
        raise DefinitionError("display_name must be a string")

    version = data.get("version", 1)
    if not isinstance(version, int):
        raise DefinitionError("version must be an integer")

    entry_raw = data.get("entry") or {}
    if not isinstance(entry_raw, dict):
        raise DefinitionError("entry must be a mapping")
    entry = EntrySpec(
        method=str(entry_raw.get("method", "invoke")),
        sync=bool(entry_raw.get("sync", True)),
    )

    graph = _require(data, "graph")
    if not isinstance(graph, dict):
        raise DefinitionError("graph must be a mapping")

    graph_entry = _require(graph, "entry", "graph")
    if not isinstance(graph_entry, str) or not graph_entry.strip():
        raise DefinitionError("graph.entry must be a non-empty string")

    nodes_raw = _require(graph, "nodes", "graph")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise DefinitionError("graph.nodes must be a non-empty list")

    nodes: list[NodeSpec] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(nodes_raw):
        if not isinstance(item, dict):
            raise DefinitionError(f"graph.nodes[{i}] must be a mapping")
        nid = item.get("id")
        ntype = item.get("type")
        if not isinstance(nid, str) or not nid.strip():
            raise DefinitionError(f"graph.nodes[{i}].id must be a non-empty string")
        if not isinstance(ntype, str) or not ntype.strip():
            raise DefinitionError(f"graph.nodes[{i}].type must be a non-empty string")
        if nid in seen_ids:
            raise DefinitionError(f"Duplicate node id: {nid}")
        seen_ids.add(nid)
        config = {k: v for k, v in item.items() if k not in ("id", "type")}
        nodes.append(NodeSpec(id=nid, type=ntype, config=config))

    if graph_entry not in seen_ids:
        raise DefinitionError(f"graph.entry '{graph_entry}' is not a defined node id")

    edges_raw = graph.get("edges") or []
    if not isinstance(edges_raw, list):
        raise DefinitionError("graph.edges must be a list")

    edges: list[tuple[str, str]] = []
    for i, edge in enumerate(edges_raw):
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise DefinitionError(f"graph.edges[{i}] must be a [source, target] pair")
        src, tgt = edge[0], edge[1]
        if not isinstance(src, str) or not isinstance(tgt, str):
            raise DefinitionError(f"graph.edges[{i}] endpoints must be strings")
        if src not in seen_ids:
            raise DefinitionError(f"graph.edges[{i}] source '{src}' is not a node id")
        if tgt != "END" and tgt not in seen_ids:
            raise DefinitionError(f"graph.edges[{i}] target '{tgt}' is not a node id or END")
        edges.append((src, tgt))

    cond_raw = graph.get("conditional_edges") or []
    if not isinstance(cond_raw, list):
        raise DefinitionError("graph.conditional_edges must be a list")

    conditional_edges: list[ConditionalEdgeSpec] = []
    for i, item in enumerate(cond_raw):
        if not isinstance(item, dict):
            raise DefinitionError(f"graph.conditional_edges[{i}] must be a mapping")
        if "from" in item and "source" not in item:
            raise DefinitionError(
                f"graph.conditional_edges[{i}]: use 'source' (not 'from') "
                "for the originating node id"
            )
        source = item.get("source")
        router = item.get("router")
        mapping = item.get("mapping")
        config = item.get("config", {})
        if not isinstance(source, str) or source not in seen_ids:
            raise DefinitionError(
                f"graph.conditional_edges[{i}].source must be a known node id"
            )
        if not isinstance(router, str) or not router.strip():
            raise DefinitionError(
                f"graph.conditional_edges[{i}].router must be a non-empty string"
            )
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise DefinitionError(
                f"graph.conditional_edges[{i}].config must be a mapping if present"
            )
        if not isinstance(mapping, dict) or not mapping:
            raise DefinitionError(
                f"graph.conditional_edges[{i}].mapping must be a non-empty mapping"
            )
        for key, dest in mapping.items():
            if not isinstance(key, str) or not isinstance(dest, str):
                raise DefinitionError(
                    f"graph.conditional_edges[{i}].mapping keys/values must be strings"
                )
            if dest != "END" and dest not in seen_ids:
                raise DefinitionError(
                    f"graph.conditional_edges[{i}].mapping target '{dest}' "
                    "is not a node id or END"
                )
        conditional_edges.append(
            ConditionalEdgeSpec(
                source=source,
                router=router,
                mapping=dict(mapping),
                config=dict(config),
            )
        )

    return AgentDefinition(
        agent_id=agent_id,
        display_name=display_name,
        version=version,
        entry=entry,
        graph_entry=graph_entry,
        nodes=tuple(nodes),
        edges=tuple(edges),
        conditional_edges=tuple(conditional_edges),
        raw=data,
    )
