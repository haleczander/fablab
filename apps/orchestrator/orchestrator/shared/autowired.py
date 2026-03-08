from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, TypeVar, cast, get_args, get_origin, get_type_hints

T = TypeVar("T")


def _normalize_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


class AutowiredDescriptor:
    def __init__(self, registry: "ResolverRegistry") -> None:
        self._registry = registry
        self._name = ""
        self._cache_name = ""

    def __set_name__(self, owner: type[object], name: str) -> None:
        self._name = name
        self._cache_name = f"__autowired_{name}"

    def __get__(self, instance: object | None, owner: type[object]) -> Any:
        if instance is None:
            return self
        cached = getattr(instance, self._cache_name, None)
        if cached is not None:
            return cached
        hints = get_type_hints(owner)
        dependency_type = _normalize_annotation(hints.get(self._name))
        if dependency_type is None:
            raise AttributeError(f"Aucune annotation pour {owner.__name__}.{self._name}")
        value = self._registry.get(dependency_type)
        setattr(instance, self._cache_name, value)
        return value


@dataclass
class BindingSpec:
    resolver: Any
    singleton: bool = False
    _instance: object | None = None
    _lock: Lock | None = None

    def resolve(self) -> object:
        if not self.singleton:
            return self.resolver()
        if self._lock is None:
            self._lock = Lock()
        if self._instance is not None:
            return self._instance
        with self._lock:
            if self._instance is None:
                self._instance = self.resolver()
        return self._instance


class ResolverRegistry:
    def __init__(self) -> None:
        self._resolvers: dict[type[Any], Any] = {}

    def register(self, target: type[Any], resolver: Any) -> None:
        self._resolvers[target] = resolver

    def register_many(self, resolvers: dict[type[Any], Any]) -> None:
        self._resolvers.update(resolvers)

    def get(self, target: type[T]) -> T:
        resolver = self._resolvers.get(target)
        if resolver is None:
            raise KeyError(f"Aucun binding pour {target!r}")
        if isinstance(resolver, BindingSpec):
            return cast(T, resolver.resolve())
        return cast(T, resolver())

    def autowired(self) -> AutowiredDescriptor:
        return AutowiredDescriptor(self)


registry = ResolverRegistry()


def autowired() -> AutowiredDescriptor:
    return registry.autowired()
