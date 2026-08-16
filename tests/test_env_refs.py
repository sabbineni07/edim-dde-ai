"""Unit tests for ``${ENV:VAR}`` binding refs."""

from __future__ import annotations

import pytest

from edim_dde_ai.core.env_refs import EnvRefError, resolve_env_ref


def test_resolve_none_and_blank():
    assert resolve_env_ref(None) is None
    assert resolve_env_ref("") is None
    assert resolve_env_ref("   ") is None


def test_resolve_literal():
    assert resolve_env_ref("https://example.com") == "https://example.com"


def test_resolve_env_ref_ok():
    env = {"EDIM_FOUNDRY_ENDPOINT_RCA": "https://rca.example.com"}
    assert (
        resolve_env_ref(
            "${ENV:EDIM_FOUNDRY_ENDPOINT_RCA}",
            environ=env,
            field_path="bindings.llm.endpoint",
        )
        == "https://rca.example.com"
    )


def test_resolve_env_ref_missing_fail_closed():
    with pytest.raises(EnvRefError, match="missing or empty"):
        resolve_env_ref(
            "${ENV:EDIM_MISSING}",
            environ={},
            field_path="bindings.llm.endpoint",
        )


def test_resolve_env_ref_empty_fail_closed():
    with pytest.raises(EnvRefError, match="missing or empty"):
        resolve_env_ref(
            "${ENV:EDIM_EMPTY}",
            environ={"EDIM_EMPTY": "  "},
        )
