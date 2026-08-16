"""Persist CLI-registered YAML paths across process invocations.

Business purpose:
  The CLI remembers paths in a JSON store so ``list`` / ``run`` can reload agents
  without re-passing files. Override location with ``EDIM_DDE_AI_STORE``.

Public API:
  - ``store_path()``
  - ``remember_paths(paths)``
  - ``load_remembered_into_registry(*, overwrite=True)``
  - ``clear_store()``

Default: ``~/.edim-dde-ai/registered_paths.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_DEFAULT_STORE = Path.home() / ".edim-dde-ai" / "registered_paths.json"
_ENV_STORE = "EDIM_DDE_AI_STORE"


def store_path() -> Path:
    """Return the CLI registry store file path.

    Override with env ``EDIM_DDE_AI_STORE`` (absolute or relative file path).
    Default: ``~/.edim-dde-ai/registered_paths.json``.

    Returns:
        Path to the JSON list of remembered YAML paths.
    """
    override = os.environ.get(_ENV_STORE)
    if override:
        return Path(override).expanduser()
    return _DEFAULT_STORE


def _load_paths() -> list[str]:
    """Read remembered paths; return ``[]`` on missing/corrupt store."""
    path = store_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(p) for p in data]


def _save_paths(paths: list[str]) -> None:
    """Write de-duplicated paths (order preserved) to the store file."""
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # de-dupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    path.write_text(json.dumps(unique, indent=2), encoding="utf-8")


def remember_paths(paths: list[str | Path]) -> None:
    """Append resolved paths to the persistent store.

    Args:
        paths: YAML paths to remember (resolved to absolute).
    """
    current = _load_paths()
    for p in paths:
        current.append(str(Path(p).resolve()))
    _save_paths(current)


def load_remembered_into_registry(*, overwrite: bool = True) -> list[str]:
    """Re-register all remembered YAML paths into the in-memory registry.

    Args:
        overwrite: Passed to ``register_from_yaml``.

    Returns:
        Agent ids successfully registered (skips missing files).
    """
    from edim_dde_ai.api.entrypoints import register_from_yaml

    ids: list[str] = []
    for path in _load_paths():
        if Path(path).is_file():
            ids.append(register_from_yaml(path, overwrite=overwrite))
    return ids


def clear_store() -> None:
    """Delete the store file if present (best-effort)."""
    try:
        store_path().unlink(missing_ok=True)
    except (OSError, PermissionError):
        pass
