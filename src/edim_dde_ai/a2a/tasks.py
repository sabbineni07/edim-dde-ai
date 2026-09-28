"""Durable A2A async task store (ADR-002 follow-on).

Stores accepted Agent1→Agent2 work so clients can poll ``task_id`` until
``completed`` / ``input_needed`` / ``error``. Backends:

* ``memory`` (default) — process-local
* ``file`` — JSON files under ``EDIM_A2A_TASK_DIR`` (survive API restart on
  the same host)

Queue-scaled ACA / Service Bus workers remain a later enterprise step; this
module is the contract + local durable path.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

ENV_TASK_STORE = "EDIM_A2A_TASK_STORE"
ENV_TASK_DIR = "EDIM_A2A_TASK_DIR"

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_INPUT_NEEDED = "input_needed"
STATUS_ERROR = "error"

_LOCK = threading.Lock()
_STORE: TaskStore | None = None


class TaskStore(Protocol):
    """Persist A2A async task records."""

    def upsert(self, record: dict[str, Any]) -> None: ...

    def get(self, task_id: str) -> dict[str, Any] | None: ...

    def clear(self) -> None: ...


class MemoryTaskStore:
    """Process-local task map."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def upsert(self, record: dict[str, Any]) -> None:
        tid = str(record.get("task_id") or "").strip()
        if not tid:
            raise ValueError("task_id required")
        with self._lock:
            self._items[tid] = dict(record)

    def get(self, task_id: str) -> dict[str, Any] | None:
        tid = (task_id or "").strip()
        if not tid:
            return None
        with self._lock:
            rec = self._items.get(tid)
            return dict(rec) if rec else None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class FileTaskStore:
    """One JSON file per task under ``root`` (atomic replace)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, task_id: str) -> Path:
        safe = "".join(c for c in task_id if c.isalnum() or c in "-_")
        if not safe or safe != task_id:
            raise ValueError(f"invalid task_id for file store: {task_id!r}")
        return self.root / f"{safe}.json"

    def upsert(self, record: dict[str, Any]) -> None:
        tid = str(record.get("task_id") or "").strip()
        if not tid:
            raise ValueError("task_id required")
        path = self._path(tid)
        tmp = path.with_suffix(".json.tmp")
        payload = json.dumps(record, default=str, sort_keys=True)
        with self._lock:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)

    def get(self, task_id: str) -> dict[str, Any] | None:
        tid = (task_id or "").strip()
        if not tid:
            return None
        path = self._path(tid)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("a2a task file read failed %s: %s", path, exc)
            return None

    def clear(self) -> None:
        with self._lock:
            for path in self.root.glob("*.json"):
                try:
                    path.unlink()
                except OSError:
                    pass


def configure_task_store_from_env() -> TaskStore:
    """Install task store from ``EDIM_A2A_TASK_STORE`` (memory|file)."""
    global _STORE
    name = (os.environ.get(ENV_TASK_STORE) or "memory").strip().lower() or "memory"
    if name == "file":
        root = (os.environ.get(ENV_TASK_DIR) or "").strip() or ".edim/a2a-tasks"
        store: TaskStore = FileTaskStore(root)
    else:
        store = MemoryTaskStore()
    with _LOCK:
        _STORE = store
    logger.info("a2a_task_store_configured", extra={"backend": name})
    return store


def get_task_store() -> TaskStore:
    """Return the configured task store (lazy default: memory)."""
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = MemoryTaskStore()
        return _STORE


def set_task_store(store: TaskStore) -> None:
    """Replace the process task store (tests)."""
    global _STORE
    with _LOCK:
        _STORE = store


def clear_a2a_tasks() -> None:
    """Drop all tasks in the active store (tests)."""
    get_task_store().clear()


def accept_task(
    *,
    agent_id: str,
    request_id: str,
    conversation_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persist a new task in ``running`` state awaiting worker execution."""
    now = time.time()
    task_id = str(uuid.uuid4())
    rec = {
        "task_id": task_id,
        "agent_id": agent_id,
        "request_id": request_id,
        "conversation_id": conversation_id,
        "status": STATUS_RUNNING,
        "payload": dict(payload),
        "state": {},
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    get_task_store().upsert(rec)
    return dict(rec)


def get_task(task_id: str) -> dict[str, Any] | None:
    """Return one task record or ``None``."""
    return get_task_store().get(task_id)


def update_task(task_id: str, **fields: Any) -> dict[str, Any] | None:
    """Merge fields into an existing task; return updated record or ``None``."""
    store = get_task_store()
    rec = store.get(task_id)
    if rec is None:
        return None
    out = dict(rec)
    out.update(fields)
    out["task_id"] = rec["task_id"]
    out["updated_at"] = time.time()
    store.upsert(out)
    return out
