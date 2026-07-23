"""Load agent definitions from YAML files and directories.

Reads YAML, then delegates validation to ``parse_agent_definition``. Raises
``LoaderError`` for I/O / YAML issues; ``DefinitionError`` for schema issues.

Example::

    from edim_dde_ai.core.loader import load_yaml, load_directory

    defn = load_yaml("demo.agent.yaml")
    defs = load_directory("./agents", pattern="*.agent.yaml")
"""


from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

import yaml

from edim_dde_ai.core.definition import AgentDefinition, parse_agent_definition
from edim_dde_ai.errors import LoaderError


def _read_yaml(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoaderError(f"Cannot read file: {path}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise LoaderError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        raise LoaderError(f"Empty YAML file: {path}")
    if not isinstance(data, dict):
        raise LoaderError(f"YAML root must be a mapping: {path}")
    return data


def load_yaml(path: str | Path) -> AgentDefinition:
    """Load and validate a single agent YAML file.

    Sets ``AgentDefinition.source_path`` to the resolved file path so relative
    ``content_dir`` entries can be resolved at ``register_agent`` time.
    """
    p = Path(path)
    if not p.is_file():
        raise LoaderError(f"Not a file: {p}")
    resolved = p.resolve()
    definition = parse_agent_definition(_read_yaml(resolved))
    return replace(definition, source_path=str(resolved))


def load_paths(paths: Iterable[str | Path]) -> list[AgentDefinition]:
    """Load multiple YAML paths."""
    defs: list[AgentDefinition] = []
    for path in paths:
        defs.append(load_yaml(path))
    return defs


def load_directory(
    directory: str | Path,
    pattern: str = "*.agent.yaml",
) -> list[AgentDefinition]:
    """Load all matching agent YAML files from a directory (non-recursive)."""
    d = Path(directory)
    if not d.is_dir():
        raise LoaderError(f"Not a directory: {d}")
    files = sorted(d.glob(pattern))
    if not files:
        raise LoaderError(f"No files matching '{pattern}' in {d}")
    return [load_yaml(f) for f in files]
