"""Normalized block contract shared by render, measure, and resource loading."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .measure import measure_block_size
from .registry import BLOCK_RENDERERS, render_block

_NESTED_KEYS = ("children", "blocks", "left", "right")
_RESOURCE_KEYS = {"src", "url", "resource", "resources", "icon"}


def _child(value: Any) -> "BlockSpec | Any":
    if isinstance(value, dict) and "type" in value:
        return BlockSpec.from_dict(value)
    if isinstance(value, list):
        return [_child(item) for item in value]
    return value


@dataclass(frozen=True)
class BlockSpec:
    type: str
    data: dict[str, Any]
    prefetch_errors: dict[str, str] = field(default_factory=dict, compare=False)

    @classmethod
    def from_dict(cls, block: dict[str, Any]) -> "BlockSpec":
        if not isinstance(block, dict) or not str(block.get("type") or "").strip():
            raise ValueError("block type is required")
        data = deepcopy(block)
        for key in _NESTED_KEYS:
            if key in data:
                data[key] = _child(data[key])
        return cls(type=str(data["type"]).strip(), data=data)

    @property
    def children(self) -> list["BlockSpec"]:
        value = self.data.get("children", [])
        return value if isinstance(value, list) else []

    def to_dict(self) -> dict[str, Any]:
        def unwrap(value: Any) -> Any:
            if isinstance(value, BlockSpec):
                return value.to_dict()
            if isinstance(value, list):
                return [unwrap(item) for item in value]
            if isinstance(value, dict):
                return {key: unwrap(item) for key, item in value.items()}
            return deepcopy(value)
        return unwrap(self.data)

    def validate(self) -> "BlockSpec":
        if self.type not in BLOCK_RENDERERS:
            raise ValueError(f"unknown block type: {self.type}")
        children = self.data.get("children")
        if children is not None and not isinstance(children, list):
            raise ValueError(f"invalid children for block: {self.type}")
        if self.type == "image" and not any(self.data.get(key) for key in ("src", "url", "resource", "field")):
            raise ValueError("invalid image resource")
        if self.type == "progress_bar":
            for key in ("value", "max"):
                if key in self.data:
                    try:
                        float(self.data[key])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"invalid progress_bar {key}") from exc
        if self.type == "two_column":
            for key in ("left", "right"):
                if key in self.data and not isinstance(self.data[key], list):
                    raise ValueError(f"invalid two_column {key}")
        for key in _NESTED_KEYS:
            value = self.data.get(key)
            values = value if isinstance(value, list) else [value]
            for child in values:
                if isinstance(child, BlockSpec):
                    child.validate()
        return self

    def render(self, ctx: Any) -> None:
        self.validate()
        render_block(ctx, self.to_dict())

    def measure(self, ctx: Any, max_width: int) -> tuple[int, int]:
        self.validate()
        size = measure_block_size(ctx, self.to_dict(), max_width)
        if hasattr(ctx, "y"):
            ctx.y += size[1]
        return size

    async def prefetch(self, fetcher: Callable[[str], Awaitable[bytes]]) -> dict[str, bytes]:
        self.validate()
        self.prefetch_errors.clear()
        resources = {}
        for resource in sorted(self.collect_resources()):
            try:
                value = await fetcher(resource)
                data = value if isinstance(value, bytes) else getattr(value, "data", None)
                if not isinstance(data, bytes):
                    raise TypeError("prefetcher must return bytes or MediaFetchResult")
                resources[resource] = data
            except Exception as exc:
                self.prefetch_errors[resource] = str(exc)
        return resources

    async def prefetch_with_media_fetcher(self, fetcher: Callable[[str], Any]) -> dict[str, bytes]:
        async def fetch(resource: str) -> Any:
            return await asyncio.to_thread(fetcher, resource)

        return await self.prefetch(fetch)

    def collect_resources(self) -> set[str]:
        resources: set[str] = set()

        def collect(value: Any, key: str | None = None) -> None:
            if isinstance(value, BlockSpec):
                for child_key, child_value in value.data.items():
                    collect(child_value, child_key)
            elif isinstance(value, dict):
                for child_key, child_value in value.items():
                    collect(child_value, child_key)
            elif isinstance(value, list):
                for item in value:
                    collect(item, key)
            elif key in _RESOURCE_KEYS and isinstance(value, str) and value.strip():
                resources.add(value.strip())

        collect(self)
        return resources
