"""Unit tests for device enumeration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voicechanger.device import DeviceMonitor, parse_aplay_output, parse_arecord_output

SAMPLE_APLAY_OUTPUT = """\
**** List of PLAYBACK Hardware Devices ****
card 0: PCH [HDA Intel PCH], device 0: ALC887-VD Analog [ALC887-VD Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: USB [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""

SAMPLE_ARECORD_OUTPUT = """\
**** List of CAPTURE Hardware Devices ****
card 1: USB [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""


class TestParseAplayOutput:
    """Test parsing aplay -l output."""

    def test_parse_output_devices(self) -> None:
        devices = parse_aplay_output(SAMPLE_APLAY_OUTPUT)
        assert len(devices) == 2
        assert devices[0]["card"] == 0
        assert devices[0]["name"] == "PCH"
        assert devices[1]["card"] == 1
        assert devices[1]["name"] == "USB"

    def test_empty_output(self) -> None:
        devices = parse_aplay_output("")
        assert devices == []

    def test_no_devices_output(self) -> None:
        devices = parse_aplay_output("**** List of PLAYBACK Hardware Devices ****\n")
        assert devices == []


class TestParseArecordOutput:
    """Test parsing arecord -l output."""

    def test_parse_input_devices(self) -> None:
        devices = parse_arecord_output(SAMPLE_ARECORD_OUTPUT)
        assert len(devices) == 1
        assert devices[0]["card"] == 1
        assert devices[0]["name"] == "USB"

    def test_empty_output(self) -> None:
        devices = parse_arecord_output("")
        assert devices == []


class TestDeviceMonitor:
    """Test DeviceMonitor class."""

    @patch("voicechanger.device._run_command")
    def test_default_device_fallback(self, mock_run: MagicMock) -> None:
        mock_run.return_value = ""
        monitor = DeviceMonitor()
        inputs = monitor.list_input_devices()
        # Should at least return something (possibly empty list without hardware)
        assert isinstance(inputs, list)

    @patch("voicechanger.device._run_command")
    def test_list_output_devices(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SAMPLE_APLAY_OUTPUT
        monitor = DeviceMonitor()
        outputs = monitor.list_output_devices()
        assert len(outputs) == 2

    @patch("voicechanger.device._run_command")
    def test_preferred_device_detection(self, mock_run: MagicMock) -> None:
        mock_run.return_value = SAMPLE_ARECORD_OUTPUT
        monitor = DeviceMonitor(preferred_input="USB")
        inputs = monitor.list_input_devices()
        assert any(d["name"] == "USB" for d in inputs)
