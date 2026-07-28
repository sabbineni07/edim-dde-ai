"""Desugar ``graph.routes`` YAML sugar into ``conditional_edges``.

``routes`` is optional convenience syntax. It expands into standard
``conditional_edges`` (router + mapping) before validation. Explicit
``conditional_edges`` are kept and appended after desugared routes.

Supported forms::

    routes:
      # Boolean / compare branch
      - after: recommend          # alias: source
        when:
          field: include_explanation
          op: truthy              # truthy | equals | in | compare
        then: explain
        else: END

      - after: score
        when:
          field: score
          op: equals
          value: 1
        then: high
        else: low

      - after: status
        when:
          field: status
          op: in
          values: [ok, warn]
        then: continue
        else: stop

      - after: n
        when:
          field: n
          op: compare
          cmp: gt                 # eq|ne|lt|le|gt|ge
          value: 10
        then: big
        else: small

      # Multi-way switch on a field value
      - after: classify
        switch: category
        cases:
          oom: handle_oom
          timeout: handle_timeout
        else: handle_other        # optional; default label \"default\"
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.errors import DefinitionError


def _source_of(item: dict[str, Any], index: int) -> str:
    source = item.get("source", item.get("after"))
    if not isinstance(source, str) or not source.strip():
        raise DefinitionError(
            f"graph.routes[{index}] must set 'after' or 'source' (origin node id)"
        )
    return source


def _desugar_when(item: dict[str, Any], index: int) -> dict[str, Any]:
    when = item.get("when")
    if not isinstance(when, dict):
        raise DefinitionError(f"graph.routes[{index}].when must be a mapping")
    field = when.get("field")
    if not isinstance(field, str) or not field.strip():
        raise DefinitionError(f"graph.routes[{index}].when.field must be a non-empty string")
    op = when.get("op", "truthy")
    if not isinstance(op, str) or not op.strip():
        raise DefinitionError(f"graph.routes[{index}].when.op must be a non-empty string")
    op = op.strip().lower()

    then = item.get("then")
    els = item.get("else")
    if not isinstance(then, str) or not then.strip():
        raise DefinitionError(f"graph.routes[{index}].then must be a non-empty string")
    if not isinstance(els, str) or not els.strip():
        raise DefinitionError(f"graph.routes[{index}].else must be a non-empty string")

    true_label = "yes"
    false_label = "no"
    mapping = {true_label: then, false_label: els}

    if op == "truthy":
        return {
            "source": _source_of(item, index),
            "router": "field_truthy",
            "config": {
                "field": field,
                "true_label": true_label,
                "false_label": false_label,
            },
            "mapping": mapping,
        }
    if op == "equals":
        if "value" not in when:
            raise DefinitionError(f"graph.routes[{index}].when.equals requires 'value'")
        return {
            "source": _source_of(item, index),
            "router": "field_equals",
            "config": {
                "field": field,
                "value": when["value"],
                "true_label": true_label,
                "false_label": false_label,
            },
            "mapping": mapping,
        }
    if op == "in":
        values = when.get("values")
        if not isinstance(values, list) or not values:
            raise DefinitionError(
                f"graph.routes[{index}].when.in requires non-empty 'values' list"
            )
        return {
            "source": _source_of(item, index),
            "router": "field_in",
            "config": {
                "field": field,
                "values": list(values),
                "true_label": true_label,
                "false_label": false_label,
            },
            "mapping": mapping,
        }
    if op == "compare":
        cmp_op = when.get("cmp") or when.get("compare")
        if not isinstance(cmp_op, str) or not cmp_op.strip():
            raise DefinitionError(
                f"graph.routes[{index}].when.compare requires 'cmp' "
                "(eq|ne|lt|le|gt|ge)"
            )
        if "value" not in when:
            raise DefinitionError(f"graph.routes[{index}].when.compare requires 'value'")
        return {
            "source": _source_of(item, index),
            "router": "field_compare",
            "config": {
                "field": field,
                "op": cmp_op.strip().lower(),
                "value": when["value"],
                "true_label": true_label,
                "false_label": false_label,
            },
            "mapping": mapping,
        }
    raise DefinitionError(
        f"graph.routes[{index}].when.op must be one of: "
        f"truthy, equals, in, compare (got {op!r})"
    )


def _desugar_switch(item: dict[str, Any], index: int) -> dict[str, Any]:
    field = item.get("switch")
    if not isinstance(field, str) or not field.strip():
        raise DefinitionError(f"graph.routes[{index}].switch must be a non-empty string")
    cases = item.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise DefinitionError(f"graph.routes[{index}].cases must be a non-empty mapping")
    for key, dest in cases.items():
        if not isinstance(key, str) or not isinstance(dest, str):
            raise DefinitionError(
                f"graph.routes[{index}].cases keys/values must be strings"
            )
    default_label = "default"
    mapping = dict(cases)
    if "else" in item:
        els = item["else"]
        if not isinstance(els, str) or not els.strip():
            raise DefinitionError(
                f"graph.routes[{index}].else must be a non-empty string when set"
            )
        mapping[default_label] = els
    return {
        "source": _source_of(item, index),
        "router": "choice",
        "config": {"field": field, "default": default_label},
        "mapping": mapping,
    }


def desugar_route_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert one ``routes[]`` item into a ``conditional_edges`` mapping."""
    if "switch" in item:
        if "when" in item:
            raise DefinitionError(
                f"graph.routes[{index}]: use either 'switch' or 'when', not both"
            )
        return _desugar_switch(item, index)
    if "when" in item:
        return _desugar_when(item, index)
    raise DefinitionError(
        f"graph.routes[{index}] must define 'when' (branch) or 'switch' (multi-way)"
    )


def apply_routes_sugar(graph: dict[str, Any]) -> dict[str, Any]:
    """Return a graph dict with ``routes`` expanded into ``conditional_edges``.

    Does not mutate the input. Removes ``routes`` from the result.
    """
    if "routes" not in graph:
        return graph

    routes = graph["routes"]
    if routes is None:
        out = dict(graph)
        out.pop("routes", None)
        return out
    if not isinstance(routes, list):
        raise DefinitionError("graph.routes must be a list")

    existing = graph.get("conditional_edges") or []
    if not isinstance(existing, list):
        raise DefinitionError("graph.conditional_edges must be a list")

    desugared: list[dict[str, Any]] = []
    for i, item in enumerate(routes):
        if not isinstance(item, dict):
            raise DefinitionError(f"graph.routes[{i}] must be a mapping")
        desugared.append(desugar_route_item(item, i))

    out = dict(graph)
    out.pop("routes", None)
    out["conditional_edges"] = list(desugared) + list(existing)
    return out
