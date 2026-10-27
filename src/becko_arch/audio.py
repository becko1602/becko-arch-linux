"""Bounded, callback-driven PCM audio for PortAudio/PipeWire/PulseAudio."""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import suppress
from typing import Any


class AudioIO:
    INPUT_RATE = 16000
    OUTPUT_RATE = 24000
    MAX_OUTPUT = OUTPUT_RATE * 2 * 30

    def __init__(self, input_device: int | None = None, output_device: int | None = None):
        self.input_device = input_device
        self.output_device = output_device
        self.incoming: asyncio.Queue[bytes] = asyncio.Queue(maxsize=12)
        self.muted = False
        self._output = bytearray()
        self._lock = threading.Lock()
        self._echo_until = 0.0
        self._closed = True
        self._input: Any = None
        self._speaker: Any = None
        self.input_overflows = 0

    @property
    def speaking(self) -> bool:
        return time.monotonic() < self._echo_until

    def queue_output(self, data: bytes) -> None:
        with self._lock:
            self._output.extend(data)
            if len(self._output) > self.MAX_OUTPUT:
                del self._output[: -self.MAX_OUTPUT]

    def clear_output(self) -> None:
        with self._lock:
            self._output.clear()
        self._echo_until = 0.0

    def _enqueue(self, data: bytes) -> None:
        if self._closed or self.muted:
            return
        if self.incoming.full():
            self.incoming.get_nowait()
            self.input_overflows += 1
        self.incoming.put_nowait(data)

    def start(self) -> None:
        import sounddevice as sd

        loop = asyncio.get_running_loop()
        self._closed = False

        def microphone(indata: Any, frames: int, timing: Any, status: Any) -> None:
            if not self.muted and not self.speaking and not self._closed:
                loop.call_soon_threadsafe(self._enqueue, bytes(indata))

        def speaker(outdata: Any, frames: int, timing: Any, status: Any) -> None:
            count = len(outdata)
            with self._lock:
                data = bytes(self._output[:count])
                del self._output[:count]
            outdata[:] = data + b"\x00" * (count - len(data))
            if data:
                self._echo_until = time.monotonic() + frames / self.OUTPUT_RATE + 0.25

        try:
            self._speaker = sd.RawOutputStream(
                samplerate=self.OUTPUT_RATE,
                channels=1,
                dtype="int16",
                blocksize=960,
                device=self.output_device,
                callback=speaker,
            )
            self._input = sd.RawInputStream(
                samplerate=self.INPUT_RATE,
                channels=1,
                dtype="int16",
                blocksize=640,
                device=self.input_device,
                callback=microphone,
            )
            self._speaker.start()
            self._input.start()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self._closed = True
        for stream in (self._input, self._speaker):
            if stream is not None:
                with suppress(Exception):
                    stream.abort()
                with suppress(Exception):
                    stream.close()
        self._input = self._speaker = None
        self.clear_output()
        while not self.incoming.empty():
            self.incoming.get_nowait()
