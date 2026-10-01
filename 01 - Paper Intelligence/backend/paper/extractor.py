from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # type: ignore[import-untyped]

from backend.paper.exceptions import InvalidPDFError


def _normalize_page_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _collect_pages(document: fitz.Document) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        page_text = page.get_text("text") or ""
        cleaned_text = _normalize_page_text(page_text)
        warnings: list[str] = []
        if not cleaned_text:
            warnings.append(
                f"Page {page_index + 1} contains no extractable text; OCR is required."
            )
        pages.append(
            {
                "page": page_index + 1,
                "text": cleaned_text,
                "metadata": {"width": page.rect.width, "height": page.rect.height},
                "warnings": warnings,
            }
        )
    return pages


def extract_pdf_pages(
    file_input: str | Path | bytes | bytearray,
) -> list[dict[str, Any]]:
    raw_bytes: bytes
    if isinstance(file_input, (bytes, bytearray)):
        raw_bytes = bytes(file_input)
        try:
            document = fitz.open(stream=raw_bytes, filetype="pdf")
        except Exception as exc:  # pragma: no cover - malformed PDF guard
            raise InvalidPDFError("Uploaded file is not a valid PDF.") from exc

        try:
            return _collect_pages(document)
        finally:
            document.close()

    path = Path(file_input)
    if not path.exists() or not path.is_file():
        raise InvalidPDFError("Uploaded file is not a valid PDF.")

    if path.suffix.lower() != ".pdf":
        raise InvalidPDFError("Uploaded file is not a valid PDF.")

    try:
        document = fitz.open(path)
    except Exception as exc:  # pragma: no cover - safe guard around malformed files
        raise InvalidPDFError("Uploaded file is not a valid PDF.") from exc

    try:
        return _collect_pages(document)
    finally:
        document.close()
