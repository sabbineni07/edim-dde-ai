"""Control-plane state store tests (memory + sync)."""

from __future__ import annotations

import pytest

from edim_dde_ai.api.entrypoints import register_from_dict
from edim_dde_ai.store import (
    AgentRecord,
    AuditEvent,
    MemoryStateStore,
    SessionRecord,
    clear_state_store,
    configure_state_store_from_env,
    create_state_store,
    get_state_store,
    resolve_state_store_name,
    set_state_store,
    sync_registered_agents_to_store,
)


def test_resolve_names():
    assert resolve_state_store_name("postgres") == "postgres"
    assert resolve_state_store_name("pg") == "postgres"
    assert resolve_state_store_name("cosmosdb") == "cosmos"
    assert resolve_state_store_name("") == "memory"
    with pytest.raises(ValueError):
        resolve_state_store_name("mongo")


def test_memory_crud_and_audit():
    store = MemoryStateStore()
    store.upsert_agent(
        AgentRecord(
            agent_id="cluster_tuning",
            display_name="Tuning",
            lifecycle="approved",
            owner="platform",
        )
    )
    assert store.get_agent("cluster_tuning").owner == "platform"
    assert len(store.list_agents()) == 1

    store.upsert_session(
        SessionRecord(session_id="s1", agent_id="cluster_tuning", state={"x": 1})
    )
    assert store.get_session("s1").state["x"] == 1

    store.append_audit(
        AuditEvent(event_id="e1", action="agent.upsert", agent_id="cluster_tuning")
    )
    assert store.list_audit(agent_id="cluster_tuning")[0].action == "agent.upsert"
    assert store.delete_agent("cluster_tuning")
    assert store.get_agent("cluster_tuning") is None


def test_sync_registered_agents():
    register_from_dict(
        {
            "agent_id": "demo_agent",
            "display_name": "Demo",
            "version": 2,
            "metadata": {
                "owner": "team-a",
                "risk_tier": "low",
                "lifecycle": "approved",
            },
            "graph": {
                "nodes": [{"id": "a", "type": "passthrough"}],
                "edges": [["START", "a"], ["a", "END"]],
            },
        }
    )
    store = MemoryStateStore()
    set_state_store(store)
    n = sync_registered_agents_to_store(actor="test")
    assert n >= 1
    rec = store.get_agent("demo_agent")
    assert rec is not None
    assert rec.owner == "team-a"
    assert rec.lifecycle == "approved"
    assert store.list_audit(agent_id="demo_agent")


def test_configure_memory_from_env(monkeypatch):
    monkeypatch.setenv("EDIM_STATE_STORE", "memory")
    s = configure_state_store_from_env()
    assert s.name == "memory"
    assert get_state_store().name == "memory"
    clear_state_store()


def test_postgres_requires_package_or_dsn(monkeypatch):
    monkeypatch.delenv("EDIM_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        create_state_store("postgres")
