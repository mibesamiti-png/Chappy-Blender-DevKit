"""Read-only object modifier stack snapshot for Blender Object Mode."""
from __future__ import annotations

from dataclasses import dataclass

from .context import require_active_mesh


@dataclass(frozen=True)
class ModifierSnapshot:
    name: str
    type: str
    viewport: bool
    render: bool


def modifier_snapshot(context) -> tuple[ModifierSnapshot, ...]:
    """Read modifier metadata only; never apply, reorder or edit modifiers.

    Returns a tuple of detached immutable values, not live Modifier objects.
    """
    obj = require_active_mesh(context, mode="OBJECT")
    return tuple(
        ModifierSnapshot(
            name=str(mod.name),
            type=str(mod.type),
            viewport=bool(mod.show_viewport),
            render=bool(mod.show_render),
        )
        for mod in obj.modifiers
    )
