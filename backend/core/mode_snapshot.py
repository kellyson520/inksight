"""Immutable inputs captured for one mode generation/render operation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModeSnapshot:
    persona: str
    config: dict[str, Any]
    definition: dict[str, Any]

    @classmethod
    def capture(cls, persona: str, config: dict | None, definition: dict | None) -> "ModeSnapshot":
        return cls(
            persona=str(persona).upper(),
            config=deepcopy(config or {}),
            definition=deepcopy(definition or {}),
        )
