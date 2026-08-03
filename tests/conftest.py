"""Shared fixtures — reset registries between tests."""

from __future__ import annotations

import pytest

from edim_dde_ai.content.registry import clear_content_providers
from edim_dde_ai.observability import clear_observability_provider
from edim_dde_ai.store import clear_state_store
from edim_dde_ai.registry.agents import clear_agent_registry
from edim_dde_ai.registry.chains import clear_chain_invokers
from edim_dde_ai.registry.nodes import clear_node_registry
from edim_dde_ai.registry.routers import clear_routers


def _clear_all() -> None:
    clear_agent_registry()
    clear_chain_invokers()
    clear_node_registry(keep_builtins=True)
    clear_routers(keep_builtins=True)
    clear_content_providers()
    clear_observability_provider()
    clear_state_store()


@pytest.fixture(autouse=True)
def _reset_registries():
    _clear_all()
    yield
    _clear_all()
