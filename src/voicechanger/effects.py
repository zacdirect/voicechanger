"""Effect type registry and parameter validation."""

from __future__ import annotations

import warnings
from typing import Any


class EffectValidationError(Exception):
    """Raised when an effect fails validation."""


# Parameter schema:
# {param_name: {"type": type, "min": float|None, "max": float|None, "default": value}}
_ParamSchema = dict[str, dict[str, Any]]

EFFECT_REGISTRY: dict[str, dict[str, Any]] = {
    "LivePitchShift": {
        "params": {
            "semitones": {"type": float, "min": -24.0, "max": 24.0, "default": 0.0},
        },
    },
    "PitchShift": {
        "params": {
            "semitones": {"type": float, "min": -24.0, "max": 24.0, "default": 0.0},
        },
    },
    "Gain": {
        "params": {
            "gain_db": {"type": float, "min": -80.0, "max": 80.0, "default": 0.0},
        },
    },
    "Reverb": {
        "params": {
            "room_size": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
            "damping": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
            "wet_level": {"type": float, "min": 0.0, "max": 1.0, "default": 0.33},
            "dry_level": {"type": float, "min": 0.0, "max": 1.0, "default": 0.4},
            "width": {"type": float, "min": 0.0, "max": 1.0, "default": 1.0},
            "freeze_mode": {"type": float, "min": 0.0, "max": 1.0, "default": 0.0},
        },
    },
    "Chorus": {
        "params": {
            "rate_hz": {"type": float, "min": 0.0, "max": 100.0, "default": 1.0},
            "depth": {"type": float, "min": 0.0, "max": 1.0, "default": 0.25},
            "centre_delay_ms": {"type": float, "min": 0.0, "max": 100.0, "default": 7.0},
            "feedback": {"type": float, "min": -1.0, "max": 1.0, "default": 0.0},
            "mix": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
        },
    },
    "Distortion": {
        "params": {
            "drive_db": {"type": float, "min": 0.0, "max": 100.0, "default": 25.0},
        },
    },
    "Delay": {
        "params": {
            "delay_seconds": {"type": float, "min": 0.0, "max": 10.0, "default": 0.5},
            "feedback": {"type": float, "min": 0.0, "max": 1.0, "default": 0.0},
            "mix": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
        },
    },
    "Compressor": {
        "params": {
            "threshold_db": {"type": float, "min": -80.0, "max": 0.0, "default": -20.0},
            "ratio": {"type": float, "min": 1.0, "max": 100.0, "default": 4.0},
            "attack_ms": {"type": float, "min": 0.0, "max": 1000.0, "default": 1.0},
            "release_ms": {"type": float, "min": 0.0, "max": 5000.0, "default": 100.0},
        },
    },
    "Limiter": {
        "params": {
            "threshold_db": {"type": float, "min": -80.0, "max": 0.0, "default": -10.0},
            "release_ms": {"type": float, "min": 0.0, "max": 5000.0, "default": 100.0},
        },
    },
    "NoiseGate": {
        "params": {
            "threshold_db": {"type": float, "min": -80.0, "max": 0.0, "default": -40.0},
            "ratio": {"type": float, "min": 1.0, "max": 100.0, "default": 10.0},
            "attack_ms": {"type": float, "min": 0.0, "max": 1000.0, "default": 1.0},
            "release_ms": {"type": float, "min": 0.0, "max": 5000.0, "default": 100.0},
        },
    },
    "HighpassFilter": {
        "params": {
            "cutoff_frequency_hz": {"type": float, "min": 20.0, "max": 20000.0, "default": 80.0},
        },
    },
    "LowpassFilter": {
        "params": {
            "cutoff_frequency_hz": {
                "type": float, "min": 20.0, "max": 20000.0, "default": 20000.0,
            },
        },
    },
    "HighShelfFilter": {
        "params": {
            "cutoff_frequency_hz": {
                "type": float, "min": 20.0, "max": 20000.0, "default": 8000.0,
            },
            "gain_db": {"type": float, "min": -80.0, "max": 80.0, "default": 0.0},
            "q": {"type": float, "min": 0.01, "max": 10.0, "default": 0.707},
        },
    },
    "LowShelfFilter": {
        "params": {
            "cutoff_frequency_hz": {
                "type": float, "min": 20.0, "max": 20000.0, "default": 200.0,
            },
            "gain_db": {"type": float, "min": -80.0, "max": 80.0, "default": 0.0},
            "q": {"type": float, "min": 0.01, "max": 10.0, "default": 0.707},
        },
    },
    "PeakFilter": {
        "params": {
            "cutoff_frequency_hz": {
                "type": float, "min": 20.0, "max": 20000.0, "default": 1000.0,
            },
            "gain_db": {"type": float, "min": -80.0, "max": 80.0, "default": 0.0},
            "q": {"type": float, "min": 0.01, "max": 10.0, "default": 0.707},
        },
    },
    "Phaser": {
        "params": {
            "rate_hz": {"type": float, "min": 0.0, "max": 100.0, "default": 1.0},
            "depth": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
            "centre_frequency_hz": {
                "type": float, "min": 20.0, "max": 20000.0, "default": 1300.0,
            },
            "feedback": {"type": float, "min": -1.0, "max": 1.0, "default": 0.0},
            "mix": {"type": float, "min": 0.0, "max": 1.0, "default": 0.5},
        },
    },
    "Bitcrush": {
        "params": {
            "bit_depth": {"type": float, "min": 1.0, "max": 32.0, "default": 8.0},
        },
    },
    "Clipping": {
        "params": {
            "threshold_db": {"type": float, "min": -80.0, "max": 0.0, "default": -6.0},
        },
    },
    "Resample": {
        "params": {
            "target_sample_rate": {
                "type": float, "min": 100.0, "max": 192000.0, "default": 8000.0,
            },
        },
    },
    "GSMFullRateCompressor": {
        "params": {},
    },
    "Invert": {
        "params": {},
    },
}


def validate_effect(effect: dict[str, Any]) -> dict[str, Any] | None:
    """Validate an effect dict against the registry.

    Returns the validated (and possibly clamped) effect dict, or None if the
    effect type is unknown (with a warning).
    """
    effect_type = effect.get("type", "")
    params = effect.get("params", {})

    if effect_type not in EFFECT_REGISTRY:
        warnings.warn(
            f"Unknown effect type '{effect_type}' — skipping.",
            stacklevel=2,
        )
        return None

    schema = EFFECT_REGISTRY[effect_type]
    param_schemas = schema["params"]

    # Check for unknown parameters
    for key in params:
        if key not in param_schemas:
            raise EffectValidationError(
                f"Invalid parameter '{key}' for effect '{effect_type}'. "
                f"Valid parameters: {list(param_schemas.keys())}"
            )

    # Validate and clamp parameters
    validated_params: dict[str, Any] = {}
    for key, value in params.items():
        pschema = param_schemas[key]
        val = float(value) if isinstance(value, (int, float)) else value

        if isinstance(val, (int, float)):
            pmin = pschema.get("min")
            pmax = pschema.get("max")
            if pmin is not None and val < pmin:
                warnings.warn(
                    f"Parameter '{key}' value {val} below minimum {pmin} for '{effect_type}', "
                    f"clamping to {pmin}.",
                    stacklevel=2,
                )
                val = pmin
            if pmax is not None and val > pmax:
                warnings.warn(
                    f"Parameter '{key}' value {val} above maximum {pmax} for '{effect_type}', "
                    f"clamping to {pmax}.",
                    stacklevel=2,
                )
                val = pmax

        validated_params[key] = val

    return {"type": effect_type, "params": validated_params}


def get_effect_types() -> list[str]:
    """Return list of all known effect type names."""
    return list(EFFECT_REGISTRY.keys())
