"""Ferramenta para baixar o modelo Kokoro com antecedência."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from transformers import AutoConfig, AutoModelForTextToWaveform, AutoProcessor


def _boolean_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    value = value.strip().lower()
    return value in {"1", "true", "yes", "y"}


def download(model_name: str, cache_dir: Path | None, local_files_only: bool) -> None:
    kwargs: dict[str, object] = {}
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        kwargs["cache_dir"] = str(cache_dir)

    trust_remote_code = _boolean_env(os.environ.get("KOKORO_TRUST_REMOTE_CODE"), default=True)
    kwargs["trust_remote_code"] = trust_remote_code

    config = None
    print(f"Baixando configuração de {model_name}...")
    try:
        config = AutoConfig.from_pretrained(
            model_name,
            local_files_only=local_files_only,
            **kwargs,
        )
    except ValueError as exc:
        if not trust_remote_code:
            raise
        print(
            "Aviso: não foi possível carregar AutoConfig. Continuando com o "
            "config padrão do modelo (detalhes: %s)" % exc,
        )

    print(f"Baixando processor de {model_name}...")
    AutoProcessor.from_pretrained(model_name, local_files_only=local_files_only, **kwargs)

    print(f"Baixando modelo de {model_name}...")
    model_kwargs = dict(kwargs)
    if config is not None:
        model_kwargs["config"] = config

    AutoModelForTextToWaveform.from_pretrained(
        model_name,
        local_files_only=local_files_only,
        **model_kwargs,
    )

    print("Download concluído.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=os.environ.get("KOKORO_MODEL", "hexgrad/Kokoro-82M"),
        help="Nome ou caminho do modelo no HuggingFace",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.environ.get("KOKORO_CACHE_DIR"),
        help="Diretório de cache dos pesos (por padrão usa variável KOKORO_CACHE_DIR ou HF_HOME)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Força modo offline (falha se os arquivos não estiverem presentes)",
    )
    args = parser.parse_args()

    env_offline = _boolean_env(os.environ.get("KOKORO_OFFLINE"))
    local_files_only = args.offline or env_offline

    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else None
    if cache_dir is None:
        hf_home = os.environ.get("HF_HOME")
        cache_dir = Path(hf_home).expanduser() if hf_home else None

    download(args.model, cache_dir, local_files_only)


if __name__ == "__main__":
    main()
