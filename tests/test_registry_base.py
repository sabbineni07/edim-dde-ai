"""Tests for the generic Registry base."""

from __future__ import annotations

import pytest

from edim_dde_ai.errors import NodeRegistryError
from edim_dde_ai.registry.base import Registry
from edim_dde_ai.registry.nodes import (
    clear_node_registry,
    get_node_factory,
    list_node_types,
    register_node,
)
from edim_dde_ai.errors import RouterRegistryError
from edim_dde_ai.registry.routers import clear_routers, get_router, list_routers


def test_overwrite_rejected_by_default():
    reg: Registry[str] = Registry(kind="widget", error_cls=NodeRegistryError)
    reg.register("a", "one")
    with pytest.raises(NodeRegistryError, match="already registered"):
        reg.register("a", "two")


def test_overwrite_when_allowed():
    reg: Registry[str] = Registry(
        kind="widget", error_cls=NodeRegistryError, allow_overwrite=True
    )
    reg.register("a", "one")
    reg.register("a", "two")
    assert reg.get("a") == "two"


def test_overwrite_flag_overrides_default():
    reg: Registry[str] = Registry(kind="widget", error_cls=NodeRegistryError)
    reg.register("a", "one")
    reg.register("a", "two", overwrite=True)
    assert reg.get("a") == "two"


def test_unknown_key_includes_kind():
    reg: Registry[str] = Registry(kind="widget", error_cls=NodeRegistryError)
    with pytest.raises(NodeRegistryError, match="Unknown widget 'missing'"):
        reg.get("missing")


def test_empty_key_rejected():
    reg: Registry[str] = Registry(kind="widget", error_cls=NodeRegistryError)
    with pytest.raises(NodeRegistryError, match="non-empty"):
        reg.register("", "x")
    with pytest.raises(NodeRegistryError, match="non-empty"):
        reg.register("   ", "x")


def test_seed_restored_on_clear():
    seed = {"x": "seeded"}
    reg: Registry[str] = Registry(
        kind="widget", error_cls=NodeRegistryError, seed=seed
    )
    reg.register("y", "extra")
    assert "y" in reg.list_keys()
    reg.clear(restore_seed=True)
    assert reg.list_keys() == ["x"]
    assert reg.get("x") == "seeded"


def test_clear_without_restore():
    reg: Registry[str] = Registry(
        kind="widget", error_cls=NodeRegistryError, seed={"x": "seeded"}
    )
    reg.clear(restore_seed=False)
    assert reg.list_keys() == []


def test_node_registry_seed_restore():
    clear_node_registry(keep_builtins=False)
    assert list_node_types() == []
    clear_node_registry(keep_builtins=True)
    assert "passthrough" in list_node_types()
    assert callable(get_node_factory("passthrough"))


def test_router_seed_and_list():
    clear_routers(keep_builtins=True)
    assert "field_truthy" in list_routers()
    assert (
        get_router("field_truthy")({"field": "include_explanation"})(
            {"include_explanation": True}
        )
        == "yes"
    )


def test_field_truthy_requires_field():
    clear_routers(keep_builtins=True)
    with pytest.raises(RouterRegistryError, match="config.field"):
        get_router("field_truthy")({})


def test_decorator_register():
    reg: Registry[str] = Registry(kind="widget", error_cls=NodeRegistryError)

    @reg.register("decorated")
    def _fn():
        return "ok"

    assert reg.get("decorated") is _fn
