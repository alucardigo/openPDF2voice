"""Consumo de áudio gerado pelo TTS utilizando sounddevice."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

try:
    import numpy as np
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - dependência opcional
    raise RuntimeError(
        "Dependências de áudio não estão instaladas. Use `pip install sounddevice numpy`."
    ) from exc

if TYPE_CHECKING:  # pragma: no cover - dica para type-checkers
    import queue as queue_module


@dataclass
class _AudioState:
    playing: bool = False
    paused: bool = False
    stream: Optional[sd.OutputStream] = None


class AudioPlayer:
    """Consumidor de filas que envia áudio para a placa de som."""

    def __init__(self, queue: "queue_module.Queue[tuple[int, bytes]]") -> None:
        self.queue = queue
        self.state = _AudioState()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self) -> None:
        while True:
            sample_rate, chunk = self.queue.get()
            if sample_rate == -1:
                self.stop()
                continue
            audio = np.frombuffer(chunk, dtype=np.float32)
            audio = audio.reshape(-1, 1)
            self.state.playing = True
            self.state.paused = False
            with sd.OutputStream(samplerate=sample_rate, channels=1) as stream:
                self.state.stream = stream
                stream.write(audio)
            self.state.playing = False
            self.state.stream = None

    def pause(self) -> None:
        if self.state.stream and not self.state.paused:
            self.state.stream.stop()
            self.state.paused = True

    def resume(self) -> None:
        if self.state.stream and self.state.paused:
            self.state.stream.start()
            self.state.paused = False

    def stop(self) -> None:
        if self.state.stream:
            try:
                self.state.stream.abort()
            except sd.PortAudioError:
                pass
            self.state.stream = None
        self.state.playing = False
        self.state.paused = False
        time.sleep(0.05)
