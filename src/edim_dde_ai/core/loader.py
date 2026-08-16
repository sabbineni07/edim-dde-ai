"""Load agent definitions from YAML files and directories.

Business purpose:
  Read YAML from disk, then delegate validation to ``parse_agent_definition``.
  Sets ``source_path`` so relative ``content_dir`` resolves at register time.

Public API:
  - ``load_yaml(path)``
  - ``load_paths(paths)``
  - ``load_directory(directory, pattern=..., *, recursive=False)``

Raises ``LoaderError`` for I/O / YAML issues; ``DefinitionError`` for schema issues.

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
    """Read and parse a YAML mapping from ``path``."""
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

    Args:
        path: Path to an agent YAML file.

    Returns:
        Validated ``AgentDefinition`` with ``source_path`` set.

    Raises:
        LoaderError: Missing file / I/O / YAML parse issues.
        DefinitionError: Invalid definition shape.
    """
    p = Path(path)
    if not p.is_file():
        raise LoaderError(f"Not a file: {p}")
    resolved = p.resolve()
    definition = parse_agent_definition(_read_yaml(resolved))
    return replace(definition, source_path=str(resolved))


def load_paths(paths: Iterable[str | Path]) -> list[AgentDefinition]:
    """Load multiple YAML paths.

    Args:
        paths: Iterable of file paths.

    Returns:
        List of definitions in input order.
    """
    defs: list[AgentDefinition] = []
    for path in paths:
        defs.append(load_yaml(path))
    return defs


def load_directory(
    directory: str | Path,
    pattern: str = "*.agent.yaml",
    *,
    recursive: bool = False,
) -> list[AgentDefinition]:
    """Load matching agent YAML files from a directory.

    By default only the top level is scanned. Pass ``recursive=True`` to include
    nested folders (e.g. ``agents/<name>/<name>.agent.yaml``).

    Args:
        directory: Directory to scan.
        pattern: Glob pattern (default ``*.agent.yaml``).
        recursive: Use ``rglob`` when True.

    Returns:
        Definitions sorted by path; duplicates from odd globs are de-duped.

    Raises:
        LoaderError: Not a directory, or no matching files.
    """
    d = Path(directory)
    if not d.is_dir():
        raise LoaderError(f"Not a directory: {d}")
    files = sorted(d.rglob(pattern) if recursive else d.glob(pattern))
    # rglob can match the same file twice on some platforms if pattern is odd; unique
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        resolved = f.resolve()
        if resolved in seen or not f.is_file():
            continue
        seen.add(resolved)
        unique.append(f)
    if not unique:
        scope = "recursively under" if recursive else "in"
        raise LoaderError(f"No files matching '{pattern}' {scope} {d}")
    return [load_yaml(f) for f in unique]
