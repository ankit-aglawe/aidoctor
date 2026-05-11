from typing import Generic, TypeVar, Any

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


if __name__ == "__main__":
    cache: Cache[Any] = Cache()
    cache.set("a", 1)
    cache.set("b", "hello")
    print(cache.get("a"))
    print(cache.get("b"))
    cache.clear()
    print(cache.get("a"))
