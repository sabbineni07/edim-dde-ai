"""A2A durable task store unit tests."""

from __future__ import annotations

from edim_dde_ai.a2a.tasks import (
    FileTaskStore,
    MemoryTaskStore,
    accept_task,
    clear_a2a_tasks,
    get_task,
    set_task_store,
    update_task,
)


def test_memory_task_lifecycle():
    set_task_store(MemoryTaskStore())
    clear_a2a_tasks()
    rec = accept_task(
        agent_id="a",
        request_id="r",
        conversation_id="c",
        payload={"m": 1},
    )
    tid = rec["task_id"]
    assert get_task(tid)["status"] == "running"
    update_task(tid, status="completed", state={"ok": True})
    assert get_task(tid)["state"]["ok"] is True
    clear_a2a_tasks()


def test_file_task_store_roundtrip(tmp_path):
    set_task_store(FileTaskStore(tmp_path))
    rec = accept_task(
        agent_id="a",
        request_id="r",
        conversation_id="c",
        payload={"m": 1},
    )
    set_task_store(FileTaskStore(tmp_path))
    loaded = get_task(rec["task_id"])
    assert loaded is not None
    assert loaded["payload"]["m"] == 1
    clear_a2a_tasks()
