"""FakeAudioStream — drop-in replacement for pedalboard.io.AudioStream in tests.

Exercises real AudioPipeline logic (state machine, profile application, plugin
construction, level computation, monitor toggle) while replacing only the
hardware I/O layer.  Unlike MagicMock, this validates that the pipeline interacts
correctly with the stream interface.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class FakeAudioStream:
    """Minimal stream that satisfies the AudioPipeline contract.

    Attributes set/read by AudioPipeline.start():
        - __enter__ / __exit__  (context manager)
        - ignore_dropped_input  (bool, set by pipeline)
        - num_input_channels    (int, read by pipeline)
        - num_output_channels   (int, read by pipeline)
        - plugins               (settable, used by _apply_profile / set_monitor_enabled)
        - read(n)               (used by poll_levels)
        - close()               (used by stop / error cleanup)
    """

    def __init__(
        self,
        *,
        num_input_channels: int = 1,
        num_output_channels: int = 1,
        buffer_size: int = 256,
        fail_on_enter: bool = False,
    ) -> None:
        self.num_input_channels = num_input_channels
        self.num_output_channels = num_output_channels
        self.ignore_dropped_input: bool = False
        self._plugins: Any = None
        self._buffer_size = buffer_size
        self._fail_on_enter = fail_on_enter
        self._entered = False
        self._closed = False
        self.buffered_input_sample_count = 0

        # Track interactions for test assertions
        self.enter_count = 0
        self.exit_count = 0
        self.close_count = 0
        self.read_calls: list[int | None] = []
        self.plugins_history: list[Any] = []

    def __enter__(self) -> FakeAudioStream:
        if self._fail_on_enter:
            raise RuntimeError("Simulated device open failure")
        self._entered = True
        self.enter_count += 1
        return self

    def __exit__(self, *_: Any) -> None:
        self._entered = False
        self.exit_count += 1

    def close(self) -> None:
        self._entered = False
        self._closed = True
        self.close_count += 1

    def read(self, num_samples: int | None = None) -> np.ndarray:
        """Return a small sine-ish buffer for level metering tests."""
        self.read_calls.append(num_samples)
        n = num_samples or self._buffer_size
        t = np.linspace(0, 1, n, dtype=np.float32)
        return (0.1 * np.sin(2 * np.pi * 440 * t)).reshape(1, -1)

    @property
    def plugins(self) -> Any:  # type: ignore[override]
        return self._plugins

    @plugins.setter
    def plugins(self, value: Any) -> None:
        self._plugins = value
        self.plugins_history.append(value)


def fake_open_stream(**_kwargs: Any) -> FakeAudioStream:
    """Factory matching the _open_stream() signature."""
    return FakeAudioStream()
