"""Generic Registry — Singleton catalog pattern for keyed factories/callables.

Business purpose:
  Shared implementation for nodes, chains, routers, and agents: register by
  string key, optional seed restore on clear, optional overwrite policy.

Public API:
  - ``Registry`` — generic keyed catalog

Supports decorator or direct registration::

    @reg.register("foo")
    def factory(...): ...

    reg.register("bar", value)
"""

from __future__ import annotations

from collections.abc import ItemsView, Iterator, Mapping
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """In-process keyed catalog with optional seed restore on clear.

    Args:
        kind: Human label used in error messages (e.g. ``"node type"``).
        error_cls: Exception type for unknown/duplicate keys.
        allow_overwrite: Default overwrite policy when ``overwrite`` is omitted.
        seed: Optional builtins restored by ``clear(restore_seed=True)``.
    """

    def __init__(
        self,
        *,
        kind: str,
        error_cls: type[Exception],
        allow_overwrite: bool = False,
        seed: Mapping[str, T] | None = None,
    ) -> None:
        self._kind = kind
        self._error_cls = error_cls
        self._allow_overwrite = allow_overwrite
        self._seed: dict[str, T] = dict(seed or {})
        self._items: dict[str, T] = dict(self._seed)

    def register(
        self,
        key: str,
        value: T | None = None,
        *,
        overwrite: bool | None = None,
    ) -> Callable[[T], T] | T:
        """Register ``value`` under ``key``, or return a decorator when ``value`` is omitted.

        Args:
            key: Non-empty registry key.
            value: Item to store, or ``None`` to return a decorator.
            overwrite: Override default overwrite policy for this call.

        Returns:
            ``value`` when provided directly, else a decorator that registers
            the decorated object and returns it.

        Raises:
            error_cls: Empty key or duplicate when overwrite is disallowed.
        """
        if not isinstance(key, str) or not key.strip():
            raise self._error_cls(f"{self._kind} key must be a non-empty string")

        allow = self._allow_overwrite if overwrite is None else overwrite

        def decorator(fn: T) -> T:
            if key in self._items and not allow:
                raise self._error_cls(f"{self._kind} already registered: {key}")
            self._items[key] = fn
            return fn

        if value is not None:
            return decorator(value)
        return decorator

    def get(self, key: str) -> T:
        """Return the item for ``key``.

        Raises:
            error_cls: If ``key`` is unknown.
        """
        try:
            return self._items[key]
        except KeyError as exc:
            raise self._error_cls(f"Unknown {self._kind} '{key}'") from exc

    def list_keys(self) -> list[str]:
        """Return sorted keys."""
        return sorted(self._items.keys())

    def clear(self, *, restore_seed: bool = True) -> None:
        """Clear entries; optionally restore the seed map.

        Args:
            restore_seed: When True, re-seed builtins after clear.
        """
        self._items.clear()
        if restore_seed:
            self._items.update(self._seed)

    def items(self) -> ItemsView[str, T]:
        """Return a live view of ``(key, value)`` pairs."""
        return self._items.items()

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)
