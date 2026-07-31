"""Compiled agent cache behavior."""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml
from edim_dde_ai.registry.agents import clear_agent_cache

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


def test_create_agent_caches_compiled_graph():
    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    a = create_agent("echo_agent")
    b = create_agent("echo_agent")
    assert a is b


def test_reregister_invalidates_cache():
    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    a = create_agent("echo_agent")
    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml", overwrite=True)
    b = create_agent("echo_agent")
    assert a is not b


def test_clear_agent_cache():
    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    a = create_agent("echo_agent")
    clear_agent_cache()
    b = create_agent("echo_agent")
    assert a is not b
