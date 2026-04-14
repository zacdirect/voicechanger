"""Contract tests for voicechanger CLI device commands.

Validates CLI interface for:
- voicechanger list-devices
- voicechanger set-device input|output <deviceid>
- voicechanger device list
- voicechanger device set input|output <deviceid>
"""

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args, **kwargs):
    """Run voicechanger CLI command and return result."""
    cmd = [sys.executable, "-m", "voicechanger"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        **kwargs
    )
    return result


class TestCLIListDevices:
    """Contract tests for 'list-devices' and 'device list' commands."""

    def test_list_devices_command_exists(self):
        """Verify list-devices command is recognized."""
        result = run_cli("list-devices", "--help")
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "list-devices" in result.stdout

    def test_device_list_command_exists(self):
        """Verify 'device list' command is recognized."""
        result = run_cli("device", "list", "--help")
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "device list" in result.stdout

    def test_list_devices_default_format(self):
        """Verify list-devices outputs in human-readable format by default."""
        result = run_cli("list-devices")
        assert result.returncode == 0
        # Should show device sections
        assert "DEVICES" in result.stdout or "default" in result.stdout.lower()

    def test_list_devices_json_format(self):
        """Verify list-devices --json outputs valid JSON."""
        result = run_cli("list-devices", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "input_devices" in data
        assert "output_devices" in data
        assert isinstance(data["input_devices"], list)
        assert isinstance(data["output_devices"], list)

    def test_device_list_json_format(self):
        """Verify 'device list --json' outputs valid JSON."""
        result = run_cli("device", "list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "input_devices" in data
        assert "output_devices" in data


class TestCLISetDevice:
    """Contract tests for 'set-device' and 'device set' commands."""

    def test_set_device_requires_arguments(self):
        """Verify set-device requires device_type and device_id."""
        result = run_cli("set-device")
        assert result.returncode != 0
        assert "device_id" in result.stderr or "required" in result.stderr.lower()

    def test_set_device_requires_device_type(self):
        """Verify set-device requires input or output specification."""
        result = run_cli("set-device", "default")
        assert result.returncode != 0
        assert "input|output" in result.stderr or "{input,output}" in result.stderr

    def test_set_device_input_default(self):
        """Verify set-device input default succeeds."""
        result = run_cli("set-device", "input", "default")
        # This should succeed or fail gracefully (if no service running)
        assert result.returncode in [0, 1]  # 0 if config saved, 1 if service issues
        # Should not crash or fail with argument parsing
        assert "invalid" not in result.stderr.lower()

    def test_set_device_output_default(self):
        """Verify set-device output default succeeds."""
        result = run_cli("set-device", "output", "default")
        assert result.returncode in [0, 1]  # 0 if config saved, 1 otherwise
        assert "invalid" not in result.stderr.lower()

    def test_device_set_command_exists(self):
        """Verify 'device set' command is recognized."""
        result = run_cli("device", "set", "--help")
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "device set" in result.stdout

    def test_device_set_requires_arguments(self):
        """Verify 'device set' requires arguments."""
        result = run_cli("device", "set")
        assert result.returncode != 0


class TestCLIProductionMode:
    """Contract tests for production-mode command."""

    def test_production_mode_command_exists(self):
        """Verify production-mode command is recognized."""
        result = run_cli("production-mode", "--help")
        assert result.returncode == 0
        assert "enable" in result.stdout or "disable" in result.stdout

    def test_production_mode_requires_state(self):
        """Verify production-mode requires enable or disable."""
        result = run_cli("production-mode")
        assert result.returncode != 0
        assert "enable" in result.stderr or "disable" in result.stderr

    def test_production_mode_invalid_state(self):
        """Verify production-mode rejects invalid states."""
        result = run_cli("production-mode", "invalid")
        assert result.returncode != 0


class TestCLIDeviceAliases:
    """Contract tests verify CLI aliases work correctly."""

    def test_list_devices_equals_device_list(self):
        """Verify list-devices and device list produce same output."""
        result1 = run_cli("list-devices", "--json")
        result2 = run_cli("device", "list", "--json")

        assert result1.returncode == 0
        assert result2.returncode == 0

        data1 = json.loads(result1.stdout)
        data2 = json.loads(result2.stdout)

        # Should have same structure
        assert data1.keys() == data2.keys()

    def test_set_device_alias_matches_device_set(self):
        """Verify set-device and device set have same CLI interface."""
        # Both should require device_type and device_id
        result1 = run_cli("set-device")
        result2 = run_cli("device", "set")

        assert result1.returncode != 0
        assert result2.returncode != 0
