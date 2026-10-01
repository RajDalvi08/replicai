from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_pdf_upload_rejected():
    response = client.post(
        "/api/v1/paper/analyze", files={"file": ("bad.txt", b"not-pdf", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_PDF"


def test_large_pdf_upload_rejected():
    oversized = b"%PDF-1.4\n" + b"A" * (settings.max_upload_bytes + 1)
    response = client.post(
        "/api/v1/paper/analyze",
        files={"file": ("large.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_PDF"
