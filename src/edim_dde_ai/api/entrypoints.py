"""High-level registration helpers for YAML / paths / directories / dict / JSON.

Facade over loader + ``register_agent``. Prefer these from apps and FastAPI
startup hooks instead of wiring core modules directly.

Example::

    from edim_dde_ai.api.entrypoints import register_from_yaml, register_from_dict

    register_from_yaml("agents/demo.agent.yaml")
    register_from_dict({"agent_id": "x", "graph": {...}})
"""


from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.registry.agents import register_agent
from edim_dde_ai.core.loader import load_directory, load_paths, load_yaml


def register_from_yaml(path: str | Path, *, overwrite: bool = False) -> str:
    """Load a single YAML and register the agent. Returns agent_id."""
    definition = load_yaml(path)
    return register_agent(definition, overwrite=overwrite)


def register_from_paths(
    paths: Iterable[str | Path], *, overwrite: bool = False
) -> list[str]:
    """Load and register multiple YAML paths. Returns agent_ids."""
    ids: list[str] = []
    for definition in load_paths(paths):
        ids.append(register_agent(definition, overwrite=overwrite))
    return ids


def register_from_directory(
    directory: str | Path,
    *,
    pattern: str = "*.agent.yaml",
    overwrite: bool = False,
    recursive: bool = False,
) -> list[str]:
    """Load and register matching YAMLs in a directory. Returns agent_ids.

    Set ``recursive=True`` to discover ``*.agent.yaml`` under nested folders.
    """
    ids: list[str] = []
    for definition in load_directory(
        directory, pattern=pattern, recursive=recursive
    ):
        ids.append(register_agent(definition, overwrite=overwrite))
    return ids


def register_from_dict(data: Mapping[str, Any], *, overwrite: bool = False) -> str:
    """Parse an agent definition mapping and register it. Returns agent_id.

    Intended for FastAPI/JSON body payloads.
    """
    definition = parse_agent_definition(dict(data))
    return register_agent(definition, overwrite=overwrite)


def register_from_dicts(
    items: Iterable[Mapping[str, Any]], *, overwrite: bool = False
) -> list[str]:
    """Parse and register multiple agent definition mappings. Returns agent_ids."""
    return [register_from_dict(item, overwrite=overwrite) for item in items]


def register_from_json(payload: str | bytes, *, overwrite: bool = False) -> str:
    """Parse JSON text/bytes into an agent definition and register it. Returns agent_id."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DefinitionError(f"Invalid JSON agent definition: {exc}") from exc
    if not isinstance(data, dict):
        raise DefinitionError(
            "JSON agent definition must decode to an object (mapping), "
            f"got {type(data).__name__}"
        )
    return register_from_dict(data, overwrite=overwrite)
