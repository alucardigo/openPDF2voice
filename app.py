"""Aplicação gráfica para converter PDFs em áudio usando Kokoro TTS."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from audio_player import AudioPlayer
from pdf_reader import extract_text_from_pdf
from tts_engine import KokoroTTSEngine


@dataclass
class ReaderState:
    pdf_path: Path | None = None
    extracted_text: str = ""
    is_reading: bool = False
    is_paused: bool = False
    current_chunk: int = 0


class PDFVoiceApp:
    """Janela principal da aplicação."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.title("openPDF2Voice — Leitor PDF com IA")
        master.geometry("720x480")

        self.state = ReaderState()
        self.audio_queue: "queue.Queue[tuple[int, bytes]]" = queue.Queue()

        self.engine = KokoroTTSEngine()
        self.player = AudioPlayer(queue=self.audio_queue)

        self._build_widgets()

    # region construção UI
    def _build_widgets(self) -> None:
        container = ttk.Frame(self.master, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(container, text="Arquivo PDF")
        file_frame.pack(fill=tk.X, pady=10)

        self.file_var = tk.StringVar()
        entry = ttk.Entry(file_frame, textvariable=self.file_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5), pady=10)

        ttk.Button(
            file_frame, text="Selecionar...", command=self._on_pick_pdf
        ).pack(side=tk.LEFT, padx=(5, 10))

        voice_frame = ttk.LabelFrame(container, text="Voz")
        voice_frame.pack(fill=tk.X, pady=10)

        voice_names = [voice.label for voice in self.engine.voices]
        self.voice_map = {voice.label: voice.id for voice in self.engine.voices}

        self.voice_combo = ttk.Combobox(
            voice_frame,
            values=voice_names,
            state="readonly",
        )
        self.voice_combo.set(self.engine.default_voice.label)
        self.voice_combo.pack(fill=tk.X, padx=10, pady=10)

        control_frame = ttk.LabelFrame(container, text="Controles")
        control_frame.pack(fill=tk.X, pady=10)

        self.start_button = ttk.Button(
            control_frame, text="Ler", command=self._on_start_reading
        )
        self.start_button.pack(side=tk.LEFT, padx=5, pady=10)

        self.pause_button = ttk.Button(
            control_frame, text="Pausar", command=self._on_pause, state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = ttk.Button(
            control_frame,
            text="Continuar",
            command=self._on_resume,
            state=tk.DISABLED,
        )
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            control_frame, text="Parar", command=self._on_stop, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        status_frame = ttk.LabelFrame(container, text="Status")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.status_text.configure(state=tk.DISABLED)

    # endregion construção UI

    def _append_status(self, message: str) -> None:
        self.master.after(0, self._append_status_sync, message)

    def _append_status_sync(self, message: str) -> None:
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.configure(state=tk.DISABLED)
        self.status_text.see(tk.END)

    def _on_pick_pdf(self) -> None:
        file = filedialog.askopenfilename(
            title="Selecione um arquivo PDF",
            filetypes=[("PDF", "*.pdf")],
        )
        if not file:
            return
        self.state.pdf_path = Path(file)
        self.file_var.set(str(self.state.pdf_path))
        self._append_status(f"Arquivo selecionado: {self.state.pdf_path.name}")

    def _on_start_reading(self) -> None:
        if not self.state.pdf_path:
            messagebox.showerror("Nenhum arquivo", "Por favor, selecione um PDF primeiro.")
            return

        voice_label = self.voice_combo.get()
        voice_id = self.voice_map.get(voice_label, self.engine.default_voice.id)

        try:
            self.state.extracted_text = extract_text_from_pdf(self.state.pdf_path)
        except ValueError as exc:
            messagebox.showerror("Falha ao ler PDF", str(exc))
            return

        self._append_status("PDF carregado. Iniciando síntese de áudio...")
        self.state.is_reading = True
        self.state.is_paused = False
        self.pause_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL)
        self.resume_button.configure(state=tk.DISABLED)

        worker = threading.Thread(
            target=self._run_synthesis,
            args=(self.state.extracted_text, voice_id),
            daemon=True,
        )
        worker.start()

    def _run_synthesis(self, text: str, voice_id: str) -> None:
        try:
            for idx, (sr, chunk) in enumerate(self.engine.stream_text(text, voice_id)):
                if not self.state.is_reading:
                    break
                self.audio_queue.put((sr, chunk))
                self.state.current_chunk = idx
                self._append_status(f"Fila de áudio atualizada (bloco {idx + 1}).")
            self.audio_queue.put((-1, b""))
        except RuntimeError as exc:
            self._append_status(f"Erro na síntese: {exc}")
            self.master.after(0, lambda: messagebox.showerror("Erro na síntese", str(exc)))
        finally:
            self.master.after(0, self._reset_controls)

    def _on_pause(self) -> None:
        self.player.pause()
        self.state.is_paused = True
        self.pause_button.configure(state=tk.DISABLED)
        self.resume_button.configure(state=tk.NORMAL)
        self._append_status("Leitura pausada.")

    def _on_resume(self) -> None:
        self.player.resume()
        self.state.is_paused = False
        self.pause_button.configure(state=tk.NORMAL)
        self.resume_button.configure(state=tk.DISABLED)
        self._append_status("Leitura retomada.")

    def _on_stop(self) -> None:
        self.state.is_reading = False
        self.player.stop()
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
        self.audio_queue.put((-1, b""))
        self._append_status("Leitura interrompida.")
        self._reset_controls()

    def _reset_controls(self) -> None:
        self.state.is_reading = False
        self.pause_button.configure(state=tk.DISABLED)
        self.resume_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    app = PDFVoiceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
