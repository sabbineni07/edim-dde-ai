"""Programmatic registration entrypoints.

Business purpose:
  App/FastAPI-facing facade to load agent definitions from YAML, paths,
  directories, dicts, or JSON and register them in the process registry.

Public API:
  - ``register_from_yaml`` / ``register_from_paths`` / ``register_from_directory``
  - ``register_from_dict`` / ``register_from_dicts`` / ``register_from_json``
"""

from edim_dde_ai.api.entrypoints import (
    register_from_dict,
    register_from_dicts,
    register_from_directory,
    register_from_json,
    register_from_paths,
    register_from_yaml,
)

__all__ = [
    "register_from_yaml",
    "register_from_paths",
    "register_from_directory",
    "register_from_dict",
    "register_from_dicts",
    "register_from_json",
]
