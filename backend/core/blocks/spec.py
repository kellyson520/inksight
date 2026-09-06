"""Normalized block contract shared by render, measure, and resource loading."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

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
