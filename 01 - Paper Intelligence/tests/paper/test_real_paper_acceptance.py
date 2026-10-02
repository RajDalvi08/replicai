from pathlib import Path

import fitz

from backend.database import SessionLocal
from backend.paper.service import PaperAnalysisService


def test_real_paper_excerpt_is_processed_with_valid_evidence():
    fixture_text = Path("tests/fixtures/real_paper_excerpt.txt").read_text(encoding="utf-8")
    pdf_path = Path("tests/fixtures/acceptance_paper.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(page.rect, fixture_text, fontsize=12)
    doc.save(pdf_path)
    doc.close()

    with SessionLocal() as db:
        service = PaperAnalysisService(db)
        result = service.analyze_pdf(
            filename=pdf_path.name,
            file_bytes=pdf_path.read_bytes(),
            content_type="application/pdf",
        )

    assert result["page_count"] >= 1
    assert result["experiments"]

    experiment = result["experiments"][0]
    assert experiment["model"] == "Transformer"
    assert experiment["dataset"] == "WMT 2014 English-to-German"
    assert experiment["metric"] in {"bleu", "BLEU"}

    reported = experiment["reported_results"]
    assert reported
    assert any(float(value["value"]) > 0 for value in reported.values())
    assert any(
        item.get("quote") and "28.4 BLEU" in item.get("quote", "")
        for item in experiment.get("evidence", [])
    )
