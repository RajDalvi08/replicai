from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile


def sanitize_filename(filename: str) -> str:
    cleaned = filename.strip()
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in {".", "_", "-"})
    return cleaned or "paper.pdf"


def compute_sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def temp_pdf_from_bytes(data: bytes) -> Path:
    with NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(data)
        return Path(handle.name)
