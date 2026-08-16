"""Optional per-agent infra bindings (LLM + Search wired; cosmos/sql shape-only).

Business purpose
----------------
Agents default to process-wide settings from ``.env`` / Key Vault. When an agent
needs a different target, declare optional ``bindings.*`` in YAML using
``${ENV:VAR}`` refs for URLs/names — never embed secrets. LLM sampling knobs
(``temperature``, ``top_p``, ``top_k``, ``max_tokens``) are **literal** values.

Resolution (LLM + Search)
-------------------------
1. String keys present → ``resolve_env_ref`` (fail closed if env missing)
2. Numeric LLM knobs present → validated literals (injected into ``llm_chain``)
3. Key omitted → ``None`` (caller uses process / chain defaults)
4. Entire ``bindings`` omitted → all globals

``cosmos`` / ``sql-warehouse`` are shape-validated today; runtime injection later.

Public API
----------
* ``LlmBinding`` / ``SearchBinding`` / ``CosmosBinding`` / ``SqlWarehouseBinding``
* ``AgentBindings`` / ``parse_agent_bindings``
* ``resolve_llm_binding`` — env-resolved + literal LLM knobs (None = default)
* ``resolve_search_binding`` — env-resolved Search endpoint/index (None = default)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from edim_dde_ai.core.env_refs import resolve_env_ref
from edim_dde_ai.errors import DefinitionError


@dataclass(frozen=True)
class LlmBinding:
    """Optional LLM infra + sampling overrides from agent YAML.

    Attributes:
        endpoint: Foundry / Azure OpenAI base URL, or ``${ENV:…}``, or None.
        deployment: Deployment / model name, or ``${ENV:…}``, or None.
        temperature: Sampling temperature literal, or None.
        top_p: Nucleus sampling ``top_p`` literal, or None.
        top_k: Optional top-k literal (provider-dependent), or None.
        max_tokens: Max completion tokens literal, or None.
    """

    endpoint: str | None = None
    deployment: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class SearchBinding:
    """Optional Azure AI Search overrides for ``rag.retrieve`` nodes.

    Attributes:
        endpoint: Search service URL, or ``${ENV:…}``, or None.
        index: Physical index name for this agent's retrieve nodes, or
            ``${ENV:…}``, or None. Key stays ``EDIM_AZURE_SEARCH_KEY``.
    """

    endpoint: str | None = None
    index: str | None = None


@dataclass(frozen=True)
class CosmosBinding:
    """Optional Cosmos DB overrides (shape only until Phase 2 wiring).

    Attributes:
        endpoint: Account URL, or ``${ENV:…}``, or None.
        database: Database name, or ``${ENV:…}``, or None.
    """

    endpoint: str | None = None
    database: str | None = None


@dataclass(frozen=True)
class SqlWarehouseBinding:
    """Optional Databricks SQL warehouse overrides (shape only until Phase 2).

    YAML key is ``sql-warehouse`` (hyphen). Attributes:
        host: Workspace host, or ``${ENV:…}``, or None.
        http_path: Warehouse HTTP path, or ``${ENV:…}``, or None.
    """

    host: str | None = None
    http_path: str | None = None


@dataclass(frozen=True)
class AgentBindings:
    """Optional top-level ``bindings`` block on an agent definition.

    Attributes:
        llm: LLM plane (resolved at graph build into ``llm_chain``).
        search: Azure AI Search plane (resolved into ``rag.retrieve``).
        cosmos: Cosmos DB plane (parsed; wiring later).
        sql_warehouse: Databricks SQL warehouse (YAML: ``sql-warehouse``).
    """

    llm: LlmBinding | None = None
    search: SearchBinding | None = None
    cosmos: CosmosBinding | None = None
    sql_warehouse: SqlWarehouseBinding | None = None


@dataclass(frozen=True)
class ResolvedLlmBinding:
    """Env-resolved LLM target + literal sampling knobs.

    ``None`` fields mean use process / chain defaults.

    Attributes:
        endpoint: Concrete endpoint URL, or None.
        deployment: Concrete deployment name, or None.
        temperature / top_p / top_k / max_tokens: Literals when set on YAML.
    """

    endpoint: str | None = None
    deployment: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ResolvedSearchBinding:
    """Env-resolved Azure AI Search target for ``rag.retrieve``.

    ``None`` fields mean use process ``EDIM_AZURE_SEARCH_*`` / CORPUS_MAP.

    Attributes:
        endpoint: Concrete Search service URL, or None.
        index: Concrete physical index name, or None.
    """

    endpoint: str | None = None
    index: str | None = None


def _optional_str_field(
    block: dict[str, Any], key: str, *, path: str
) -> str | None:
    """Return a stripped non-empty string, or None when the key is omitted."""
    if key not in block or block.get(key) is None:
        return None
    value = block.get(key)
    if not isinstance(value, str) or not str(value).strip():
        raise DefinitionError(f"{path}.{key} must be a non-empty string when present")
    return str(value).strip()


def _optional_float_field(
    block: dict[str, Any], key: str, *, path: str, minimum: float, maximum: float
) -> float | None:
    """Return a float literal in ``[minimum, maximum]``, or None when omitted."""
    if key not in block or block.get(key) is None:
        return None
    value = block.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DefinitionError(f"{path}.{key} must be a number when present")
    number = float(value)
    if number < minimum or number > maximum:
        raise DefinitionError(
            f"{path}.{key} must be between {minimum} and {maximum} (got {number})"
        )
    return number


def _optional_int_field(
    block: dict[str, Any], key: str, *, path: str, minimum: int, maximum: int
) -> int | None:
    """Return an int literal in ``[minimum, maximum]``, or None when omitted."""
    if key not in block or block.get(key) is None:
        return None
    value = block.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DefinitionError(f"{path}.{key} must be an integer when present")
    if value < minimum or value > maximum:
        raise DefinitionError(
            f"{path}.{key} must be between {minimum} and {maximum} (got {value})"
        )
    return value


def _parse_named_binding(
    block: dict[str, Any],
    name: str,
    fields: tuple[str, ...],
    cls: type,
) -> Any | None:
    """Parse one bindings.<name> mapping of string fields into a frozen dataclass."""
    raw = block.get(name)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise DefinitionError(f"bindings.{name} must be a mapping when present")
    path = f"bindings.{name}"
    kwargs = {f: _optional_str_field(raw, f, path=path) for f in fields}
    return cls(**kwargs)


def _parse_llm_binding(block: dict[str, Any]) -> LlmBinding | None:
    """Parse ``bindings.llm`` (env-ref strings + literal sampling knobs)."""
    raw = block.get("llm")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise DefinitionError("bindings.llm must be a mapping when present")
    path = "bindings.llm"
    return LlmBinding(
        endpoint=_optional_str_field(raw, "endpoint", path=path),
        deployment=_optional_str_field(raw, "deployment", path=path),
        temperature=_optional_float_field(
            raw, "temperature", path=path, minimum=0.0, maximum=2.0
        ),
        top_p=_optional_float_field(
            raw, "top_p", path=path, minimum=0.0, maximum=1.0
        ),
        top_k=_optional_int_field(raw, "top_k", path=path, minimum=1, maximum=1000),
        max_tokens=_optional_int_field(
            raw, "max_tokens", path=path, minimum=1, maximum=128_000
        ),
    )


def parse_agent_bindings(data: dict[str, Any] | None) -> AgentBindings | None:
    """Parse optional ``bindings`` from an agent root mapping.

    Args:
        data: Agent definition dict (or ``None``).

    Returns:
        ``AgentBindings`` when the block is present; ``None`` when omitted.

    Raises:
        DefinitionError: Invalid shape / types.
    """
    if not data or "bindings" not in data:
        return None
    block = data.get("bindings")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise DefinitionError("bindings must be a mapping when present")

    # YAML key is hyphenated; accept underscore alias for tests / tooling.
    sql_raw_key = (
        "sql-warehouse"
        if "sql-warehouse" in block
        else ("sql_warehouse" if "sql_warehouse" in block else None)
    )
    sql_warehouse = None
    if sql_raw_key is not None:
        sql_warehouse = _parse_named_binding(
            {sql_raw_key: block[sql_raw_key]},
            sql_raw_key,
            ("host", "http_path"),
            SqlWarehouseBinding,
        )

    return AgentBindings(
        llm=_parse_llm_binding(block),
        search=_parse_named_binding(
            block, "search", ("endpoint", "index"), SearchBinding
        ),
        cosmos=_parse_named_binding(
            block, "cosmos", ("endpoint", "database"), CosmosBinding
        ),
        sql_warehouse=sql_warehouse,
    )


def resolve_llm_binding(
    bindings: AgentBindings | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ResolvedLlmBinding:
    """Resolve ``bindings.llm`` env refs; copy literal sampling knobs as-is.

    Args:
        bindings: Parsed agent bindings (may be ``None``).
        environ: Optional env map for tests.

    Returns:
        ``ResolvedLlmBinding`` with concrete strings/numbers or ``None`` per field.

    Raises:
        EnvRefError: Declared ``${ENV:…}`` missing/empty.
    """
    if bindings is None or bindings.llm is None:
        return ResolvedLlmBinding()
    llm = bindings.llm
    endpoint = resolve_env_ref(
        llm.endpoint,
        environ=environ,
        field_path="bindings.llm.endpoint",
    )
    deployment = resolve_env_ref(
        llm.deployment,
        environ=environ,
        field_path="bindings.llm.deployment",
    )
    return ResolvedLlmBinding(
        endpoint=endpoint,
        deployment=deployment,
        temperature=llm.temperature,
        top_p=llm.top_p,
        top_k=llm.top_k,
        max_tokens=llm.max_tokens,
    )


def resolve_search_binding(
    bindings: AgentBindings | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ResolvedSearchBinding:
    """Resolve ``bindings.search`` env refs for ``rag.retrieve`` injection.

    Args:
        bindings: Parsed agent bindings (may be ``None``).
        environ: Optional env map for tests.

    Returns:
        ``ResolvedSearchBinding`` with concrete strings or ``None`` per field.

    Raises:
        EnvRefError: Declared ``${ENV:…}`` missing/empty.
    """
    if bindings is None or bindings.search is None:
        return ResolvedSearchBinding()
    search = bindings.search
    endpoint = resolve_env_ref(
        search.endpoint,
        environ=environ,
        field_path="bindings.search.endpoint",
    )
    index = resolve_env_ref(
        search.index,
        environ=environ,
        field_path="bindings.search.index",
    )
    return ResolvedSearchBinding(endpoint=endpoint, index=index)
