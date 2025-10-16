"""Wrapper do modelo Kokoro para síntese de voz local."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

try:
    import numpy as np
    import torch
    from transformers import AutoModelForTextToWaveform, AutoProcessor
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Instale as dependências de IA com `pip install transformers torch numpy`."
    ) from exc


@dataclass(frozen=True)
class KokoroVoice:
    id: str
    label: str


class KokoroTTSEngine:
    """Wrapper simples para o modelo Kokoro disponível no HuggingFace."""

    def __init__(
        self,
        model_name: str = "hexgrad/Kokoro-82M",
        device: str | None = None,
        cache_dir: str | Path | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        env_model = os.environ.get("KOKORO_MODEL")
        self.model_name = env_model or model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else _resolve_cache_dir()
        self.local_files_only = _boolean_env("KOKORO_OFFLINE", False) if local_files_only is None else local_files_only

        load_kwargs: dict[str, object] = {}
        if self.cache_dir:
            load_kwargs["cache_dir"] = str(self.cache_dir)
        if self.local_files_only:
            load_kwargs["local_files_only"] = True

        self.processor = AutoProcessor.from_pretrained(self.model_name, **load_kwargs)
        self.model = AutoModelForTextToWaveform.from_pretrained(self.model_name, **load_kwargs)
        self.model.to(self.device)

        self.voices: List[KokoroVoice] = self._load_voices()
        self.default_voice = next((voice for voice in self.voices if "PT-BR" in voice.label), self.voices[0])

    def _load_voices(self) -> List[KokoroVoice]:
        """Lista de vozes suportadas baseada no arquivo VOICES.md."""
        return [
            KokoroVoice("pt_br_female_a", "PT-BR • Feminina A"),
            KokoroVoice("pt_br_male_a", "PT-BR • Masculina A"),
            KokoroVoice("pt_br_female_b", "PT-BR • Feminina B"),
            KokoroVoice("pt_br_male_b", "PT-BR • Masculina B"),
        ]

    def _chunk_text(self, text: str, max_chars: int = 400) -> Iterable[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > max_chars and current:
                yield current.strip()
                current = sentence
            else:
                current += (" " if current else "") + sentence
        if current:
            yield current.strip()

    def synthesize(self, text: str, voice_id: str) -> tuple[int, bytes]:
        sample_rate, audio = next(self.stream_text(text, voice_id))
        return sample_rate, audio

    def stream_text(self, text: str, voice_id: str) -> Iterable[tuple[int, bytes]]:
        """Gera áudio em blocos para permitir streaming na interface."""
        for chunk in self._chunk_text(text):
            inputs = self.processor(
                text=chunk,
                return_tensors="pt",
                voice_preset=voice_id,
            ).to(self.device)

            with torch.inference_mode():
                outputs = self.model(**inputs)

            waveform = getattr(outputs, "waveform", None)
            if waveform is None and hasattr(outputs, "audio_values"):
                waveform = outputs.audio_values
            if waveform is None:
                raise RuntimeError("A resposta do modelo não contém dados de áudio.")

            audio = waveform[0].cpu().numpy().astype(np.float32)
            sample_rate = getattr(self.model.config, "sampling_rate", 24000)
            yield sample_rate, audio.tobytes()


def _resolve_cache_dir() -> Path | None:
    """Determina diretório padrão de cache respeitando variáveis de ambiente."""
    value = os.environ.get("KOKORO_CACHE_DIR") or os.environ.get("HF_HOME")
    return None if not value else Path(value).expanduser()


def _boolean_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}
