"""Unit tests for effects registry."""

from __future__ import annotations

import warnings

import pytest

from voicechanger.effects import EFFECT_REGISTRY, EffectValidationError, validate_effect


class TestEffectRegistry:
    """Test effect type registry lookups."""

    def test_known_types_present(self) -> None:
        expected_types = [
            "LivePitchShift",
            "PitchShift",
            "Gain",
            "Reverb",
            "Chorus",
            "Distortion",
            "Delay",
            "Compressor",
            "Limiter",
            "NoiseGate",
        ]
        for t in expected_types:
            assert t in EFFECT_REGISTRY, f"{t} not in EFFECT_REGISTRY"

    def test_registry_has_param_schemas(self) -> None:
        gain_schema = EFFECT_REGISTRY["Gain"]
        assert "gain_db" in gain_schema["params"]

    def test_reverb_params(self) -> None:
        reverb_schema = EFFECT_REGISTRY["Reverb"]
        for param in ["room_size", "damping", "wet_level", "dry_level", "width", "freeze_mode"]:
            assert param in reverb_schema["params"]


class TestUnknownType:
    """Test handling of unknown effect types."""

    def test_unknown_type_skipped_with_warning(self) -> None:
        effect = {"type": "NonExistentEffect", "params": {"foo": 1.0}}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = validate_effect(effect)
            assert result is None
            assert len(w) == 1
            assert "NonExistentEffect" in str(w[0].message)


class TestParameterValidation:
    """Test parameter validation and clamping."""

    def test_valid_gain_params(self) -> None:
        effect = {"type": "Gain", "params": {"gain_db": 3.0}}
        validated = validate_effect(effect)
        assert validated is not None
        assert validated["params"]["gain_db"] == 3.0

    def test_param_clamping_too_high(self) -> None:
        """Out-of-range values should be clamped with warning."""
        effect = {"type": "Reverb", "params": {"room_size": 5.0}}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validated = validate_effect(effect)
            assert validated is not None
            assert validated["params"]["room_size"] <= 1.0
            assert len(w) >= 1

    def test_param_clamping_too_low(self) -> None:
        effect = {"type": "Reverb", "params": {"room_size": -1.0}}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validated = validate_effect(effect)
            assert validated is not None
            assert validated["params"]["room_size"] >= 0.0
            assert len(w) >= 1

    def test_unknown_param_raises(self) -> None:
        effect = {"type": "Gain", "params": {"nonexistent_param": 1.0}}
        with pytest.raises(EffectValidationError, match="nonexistent_param"):
            validate_effect(effect)

    def test_known_type_default_params(self) -> None:
        """Known type with empty params uses defaults."""
        effect = {"type": "Gain", "params": {}}
        validated = validate_effect(effect)
        assert validated is not None

    def test_live_pitch_shift_params(self) -> None:
        effect = {"type": "LivePitchShift", "params": {"semitones": -8.0}}
        validated = validate_effect(effect)
        assert validated is not None
        assert validated["params"]["semitones"] == -8.0
