"""Utilitário para extrair texto de arquivos PDF."""
from __future__ import annotations

from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise ValueError(
        "Dependência `pypdf` não encontrada. Instale com `pip install pypdf`."
    ) from exc


def extract_text_from_pdf(path: Path) -> str:
    """Extrai texto do PDF informado."""
    if not path.exists():
        raise ValueError(f"Arquivo não encontrado: {path}")

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(text)

    content = "\n".join(pages).strip()
    if not content:
        raise ValueError("Não foi possível extrair texto do PDF.")
    return content
