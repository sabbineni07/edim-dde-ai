"""Validate extended agent definition blocks (BL-002).

Business purpose:
  Structural graph validation remains in ``core.definition``. This module checks
  optional R1 contract blocks (metadata, model, bindings, security, evaluation, hitl, rag)
  when present, and can optionally load ``schemas/agent.schema.json`` if the
  ``jsonschema`` package is installed.

Public API:
  - ``validate_extended_blocks(data)``
  - ``validate_agent_dict(data, *, use_jsonschema=False)``
  - ``schema_path()``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from edim_dde_ai.core.bindings import parse_agent_bindings
from edim_dde_ai.errors import DefinitionError

_RISK = frozenset({"low", "medium", "high"})
_LIFECYCLE = frozenset({"draft", "review", "approved", "deprecated"})

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "agent.schema.json"
)


def validate_extended_blocks(data: dict[str, Any]) -> None:
    """Raise DefinitionError if optional contract blocks have invalid shape.

    Args:
        data: Raw agent definition mapping.

    Raises:
        DefinitionError: Invalid types/enums in optional blocks.
    """
    if not isinstance(data, dict):
        raise DefinitionError("Agent definition must be a mapping")

    metadata = data.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise DefinitionError("metadata must be a mapping")
        risk = metadata.get("risk_tier")
        if risk is not None and risk not in _RISK:
            raise DefinitionError(
                f"metadata.risk_tier must be one of {sorted(_RISK)}"
            )
        life = metadata.get("lifecycle")
        if life is not None and life not in _LIFECYCLE:
            raise DefinitionError(
                f"metadata.lifecycle must be one of {sorted(_LIFECYCLE)}"
            )
        if "hitl_required" in metadata and not isinstance(
            metadata["hitl_required"], bool
        ):
            raise DefinitionError("metadata.hitl_required must be a boolean")

    model = data.get("model")
    if model is not None:
        if not isinstance(model, dict):
            raise DefinitionError("model must be a mapping")
        ref = model.get("ref")
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            raise DefinitionError("model.ref must be a non-empty string")

    # Optional Phase 1 infra bindings (shape only; env resolve at graph build).
    parse_agent_bindings(data)

    tools = data.get("tools")
    if tools is not None and not isinstance(tools, list):
        raise DefinitionError("tools must be a list when present")

    for key in ("rag", "security", "evaluation", "hitl", "memory"):
        block = data.get(key)
        if block is None:
            continue
        if key == "rag" and block is None:
            continue
        if not isinstance(block, dict):
            raise DefinitionError(f"{key} must be a mapping or null")

    rag = data.get("rag")
    if isinstance(rag, dict):
        if "enabled" in rag and not isinstance(rag["enabled"], bool):
            raise DefinitionError("rag.enabled must be a boolean")
        if "top_k" in rag and (
            not isinstance(rag["top_k"], int) or rag["top_k"] < 1
        ):
            raise DefinitionError("rag.top_k must be a positive integer")
        mode = rag.get("search_mode")
        if mode is not None and mode not in {"vector", "keyword", "hybrid"}:
            raise DefinitionError(
                "rag.search_mode must be vector|keyword|hybrid"
            )

    security = data.get("security")
    if isinstance(security, dict) and "pii_redaction" in security:
        if not isinstance(security["pii_redaction"], bool):
            raise DefinitionError("security.pii_redaction must be a boolean")

    hitl = data.get("hitl")
    if isinstance(hitl, dict) and "enabled" in hitl:
        if not isinstance(hitl["enabled"], bool):
            raise DefinitionError("hitl.enabled must be a boolean")

    memory = data.get("memory")
    if memory is not None:
        from edim_dde_ai.session.models import MemoryPolicy

        policy = MemoryPolicy.from_raw(memory)
        if policy.enabled and data.get("session") is None:
            raise DefinitionError(
                "session block is required when memory.strategy is not none"
            )

    session = data.get("session")
    if session is not None and not isinstance(session, dict):
        raise DefinitionError("session must be a mapping or null")


def validate_agent_dict(data: dict[str, Any], *, use_jsonschema: bool = False) -> None:
    """Validate extended blocks; optionally run JSON Schema if installed.

    Args:
        data: Raw agent definition mapping.
        use_jsonschema: When True, also validate against ``agent.schema.json``.

    Raises:
        DefinitionError: Shape/schema failures, or missing ``jsonschema`` package
            when ``use_jsonschema=True``.
    """
    validate_extended_blocks(data)
    if not use_jsonschema:
        return
    try:
        import jsonschema
    except ImportError as exc:
        raise DefinitionError(
            "jsonschema is not installed; pip install jsonschema "
            "or omit use_jsonschema=True"
        ) from exc
    if not _SCHEMA_PATH.is_file():
        raise DefinitionError(f"Schema file not found: {_SCHEMA_PATH}")
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DefinitionError(f"JSON Schema validation failed: {exc.message}") from exc


def schema_path() -> Path:
    """Return the path to packaged ``schemas/agent.schema.json``.

    Returns:
        Absolute ``Path`` (may not exist in incomplete installs).
    """
    return _SCHEMA_PATH
