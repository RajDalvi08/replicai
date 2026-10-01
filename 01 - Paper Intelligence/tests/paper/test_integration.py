from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_analyze_dataset_and_persist_pdf():
    pdf_path = Path("tests/fixtures/acceptance_paper.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Experimental Setup\nBatch size: 64\nLearning rate: 0.01\nAccuracy: 87.6%",
    )
    doc.save(pdf_path)
    doc.close()

    with pdf_path.open("rb") as fh:
        response = client.post(
            "/api/v1/paper/analyze",
            files={"file": (pdf_path.name, fh.read(), "application/pdf")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["page_count"] >= 1
    assert body["experiments"]
    assert body["experiments"][0]["batch_size"] == 64
    assert body["experiments"][0]["reported_results"]["accuracy"]["value"] == 87.6
    assert body["experiments"][0]["evidence"]
    assert body["experiments"][0]["evidence"][0]["page"] >= 1
    assert body["experiments"][0]["evidence"][0]["quote"]
