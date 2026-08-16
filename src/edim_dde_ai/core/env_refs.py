"""Resolve ``${ENV:VAR}`` references from agent YAML bindings.

Business purpose
----------------
Agent ``bindings`` may name process environment variables instead of embedding
secrets or host-specific URLs. This helper is the single interpolation dialect
for those refs (distinct from sources ``${VAR}`` and prompt ``{state}`` braces).

Rules
-----
* ``${ENV:NAME}`` — required; missing/empty env → error (fail closed)
* Plain non-empty string — returned as-is (tests / rare literals)
* ``None`` / blank — treated as "not set" (caller falls back to process global)

Public API
----------
* ``ENV_REF_PATTERN`` — compiled matcher
* ``resolve_env_ref`` — resolve one value
* ``EnvRefError`` — missing or malformed ref
"""

from __future__ import annotations

import os
import re
from typing import Mapping

ENV_REF_PATTERN = re.compile(r"^\$\{ENV:([A-Za-z_][A-Za-z0-9_]*)\}$")


class EnvRefError(ValueError):
    """Raised when a declared ``${ENV:…}`` cannot be resolved."""


def resolve_env_ref(
    value: str | None,
    *,
    environ: Mapping[str, str] | None = None,
    field_path: str = "value",
) -> str | None:
    """Resolve an optional YAML string that may be an ``${ENV:VAR}`` ref.

    Args:
        value: Raw YAML string, or ``None`` / blank when the key is omitted.
        environ: Env map (default ``os.environ``).
        field_path: Label for error messages (e.g. ``bindings.llm.endpoint``).

    Returns:
        Resolved non-empty string, or ``None`` when ``value`` is unset/blank
        (caller should apply process-global fallback).

    Raises:
        EnvRefError: Malformed ``${ENV:…}``, or declared env var missing/empty.

    Example:
        >>> import os
        >>> os.environ["EDIM_FOUNDRY_ENDPOINT_RCA"] = "https://example.openai.azure.com"
        >>> resolve_env_ref("${ENV:EDIM_FOUNDRY_ENDPOINT_RCA}")
        'https://example.openai.azure.com'
        >>> resolve_env_ref(None) is None
        True
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    match = ENV_REF_PATTERN.match(text)
    if match:
        name = match.group(1)
        env = environ if environ is not None else os.environ
        resolved = str(env.get(name) or "").strip()
        if not resolved:
            raise EnvRefError(
                f"{field_path} references ${{ENV:{name}}} but that environment "
                "variable is missing or empty (fail closed; omit the binding "
                "key to use process globals instead)"
            )
        return resolved

    # Plain literal (URLs, deployment names, etc.) — allowed. Prefer ${ENV:…}
    # for host-specific values you do not want committed; never put secrets here.
    return text
