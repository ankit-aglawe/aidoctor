from typing import Generic, TypeVar

T = TypeVar("T")


class Cache(Generic[T]):
    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def get(self, key: str) -> T | None:
        return self._store.get(key)

    def set(self, key: str, value: T) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
