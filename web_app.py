"""Interface web para converter PDFs em áudio utilizando Kokoro TTS."""

from __future__ import annotations

import argparse
import io
import os
import tempfile
import uuid
import wave
from pathlib import Path

import numpy as np
from flask import (
    Flask,
    flash,
    render_template,
    request,
    send_from_directory,
)

from pdf_reader import extract_text_from_pdf
from tts_engine import KokoroTTSEngine, KokoroVoice


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "openpdf2voice")
    generated_dir = Path(os.environ.get("GENERATED_DIR", "generated")).resolve()
    generated_dir.mkdir(parents=True, exist_ok=True)
    app.config["GENERATED_DIR"] = generated_dir
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MiB por upload

    engine = KokoroTTSEngine()
    voices: list[KokoroVoice] = list(engine.voices)
    voice_ids = {voice.id for voice in voices}

    def _cleanup_generated(max_items: int = 10) -> None:
        files = sorted(
            generated_dir.glob("*.wav"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old_file in files[max_items:]:
            try:
                old_file.unlink()
            except OSError:
                pass

    def _synthesize_to_wav(text: str, voice_id: str) -> io.BytesIO:
        sample_rate: int | None = None
        chunks: list[np.ndarray] = []
        for sample_rate, chunk_bytes in engine.stream_text(text, voice_id):
            chunk = np.frombuffer(chunk_bytes, dtype=np.float32)
            chunks.append(chunk)

        if not chunks or sample_rate is None:
            raise RuntimeError("Nenhum áudio foi gerado pelo modelo.")

        # Filter out empty arrays
        non_empty_chunks = [chunk for chunk in chunks if chunk.size > 0]
        if not non_empty_chunks:
            raise RuntimeError("Nenhum áudio foi gerado pelo modelo.")

        audio = np.concatenate(non_empty_chunks)
        audio = np.clip(audio, -1.0, 1.0)
        pcm16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm16.tobytes())
        buffer.seek(0)
        return buffer

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        audio_filename: str | None = None
        selected_voice = request.form.get("voice_id") or engine.default_voice.id
        if selected_voice not in voice_ids:
            selected_voice = engine.default_voice.id

        if request.method == "POST":
            uploaded = request.files.get("pdf_file")
            if not uploaded or uploaded.filename == "":
                flash("Selecione um arquivo PDF válido.", "error")
            else:
                suffix = Path(uploaded.filename).suffix or ".pdf"
                tmp_path: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        uploaded.save(tmp.name)
                        tmp_path = Path(tmp.name)

                    text = extract_text_from_pdf(tmp_path)
                    audio_buffer = _synthesize_to_wav(text, selected_voice)

                    audio_filename = f"{uuid.uuid4().hex}.wav"
                    output_path = generated_dir / audio_filename
                    output_path.write_bytes(audio_buffer.getvalue())
                    _cleanup_generated()

                    flash("Áudio gerado com sucesso!", "success")
                except ValueError as exc:
                    flash(str(exc), "error")
                except RuntimeError as exc:
                    flash(f"Erro ao gerar áudio: {exc}", "error")
                finally:
                    if tmp_path and tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass

        return render_template(
            "index.html",
            voices=voices,
            default_voice=engine.default_voice.id,
            audio_filename=audio_filename,
            selected_voice=selected_voice,
        )

    @app.route("/audio/<path:filename>")
    def serve_audio(filename: str):
        directory = app.config["GENERATED_DIR"]
        return send_from_directory(directory, filename, mimetype="audio/wav")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Interface web do openPDF2Voice")
    parser.add_argument("--host", default="127.0.0.1", help="Host para expor a aplicação")
    parser.add_argument("--port", default=7860, type=int, help="Porta HTTP")
    parser.add_argument("--debug", action="store_true", help="Ativa modo debug do Flask")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
