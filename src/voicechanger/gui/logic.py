"""GUI data logic — slider mapping and profile building (no tkinter dependency)."""

from __future__ import annotations

from dataclasses import dataclass, field

from voicechanger.effects import EFFECT_REGISTRY
from voicechanger.profile import Profile


@dataclass
class GuiEffectState:
    """Represents an effect's state in the GUI."""

    type: str
    params: dict[str, float] = field(default_factory=dict)


def slider_to_param(effect_type: str, param_name: str, slider_value: int) -> float:
    """Convert a slider value (0-100) to a parameter value."""
    schema = EFFECT_REGISTRY.get(effect_type, {}).get("params", {})
    param_schema = schema.get(param_name)
    if param_schema is None:
        return float(slider_value)

    pmin = param_schema.get("min", 0.0)
    pmax = param_schema.get("max", 1.0)
    return pmin + (pmax - pmin) * (slider_value / 100.0)


def param_to_slider(effect_type: str, param_name: str, param_value: float) -> int:
    """Convert a parameter value to a slider value (0-100)."""
    schema = EFFECT_REGISTRY.get(effect_type, {}).get("params", {})
    param_schema = schema.get(param_name)
    if param_schema is None:
        return int(param_value)

    pmin = param_schema.get("min", 0.0)
    pmax = param_schema.get("max", 1.0)
    if pmax == pmin:
        return 50
    return int(round(100.0 * (param_value - pmin) / (pmax - pmin)))


def build_profile_from_gui_state(
    name: str,
    author: str,
    description: str,
    effects: list[GuiEffectState],
) -> Profile:
    """Build a Profile from GUI state."""
    effect_dicts = [{"type": e.type, "params": dict(e.params)} for e in effects]
    return Profile(
        name=name,
        author=author,
        description=description,
        effects=effect_dicts,
    )
