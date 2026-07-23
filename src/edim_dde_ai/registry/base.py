"""Generic Registry -- Singleton catalog pattern for keyed factories/callables.

Shared implementation for nodes, chains, routers, and agents: register by
string key, optional seed restore on clear, optional overwrite policy.

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

    Supports decorator or direct registration::

        @reg.register("foo")
        def factory(...): ...

        reg.register("bar", value)
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
        """Register ``value`` under ``key``, or return a decorator when ``value`` is omitted."""
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
        try:
            return self._items[key]
        except KeyError as exc:
            raise self._error_cls(f"Unknown {self._kind} '{key}'") from exc

    def list_keys(self) -> list[str]:
        return sorted(self._items.keys())

    def clear(self, *, restore_seed: bool = True) -> None:
        self._items.clear()
        if restore_seed:
            self._items.update(self._seed)

    def items(self) -> ItemsView[str, T]:
        return self._items.items()

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)
