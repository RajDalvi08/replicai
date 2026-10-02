from pathlib import Path

import fitz
import pytest

from backend.paper.extractor import extract_pdf_pages


def test_extract_pdf_pages_number_and_text():
    pdf_path = Path("tests/fixtures/sample_paper.pdf")
    if not pdf_path.exists():
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Experimental Setup\nBatch size: 64\nLearning rate: 0.01")
        doc.save(pdf_path)
        doc.close()

    pages = extract_pdf_pages(pdf_path)

    assert len(pages) >= 1
    assert pages[0]["page"] == 1
    assert any("Batch size" in p["text"] for p in pages)


def test_empty_pages_warn():
    pdf_path = Path("tests/fixtures/empty_pages.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    pages = extract_pdf_pages(pdf_path)

    assert len(pages) == 2
    assert any("no extractable text" in p["warnings"][0].lower() for p in pages if p["warnings"])


def test_invalid_pdf_raises():
    bad_path = Path("tests/fixtures/not_a_pdf.pdf")
    bad_path.write_bytes(b"not a real pdf")

    with pytest.raises(ValueError):
        extract_pdf_pages(bad_path)
