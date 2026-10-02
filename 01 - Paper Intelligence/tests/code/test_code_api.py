"""Tests for the Code Intelligence module - API endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.code.ingestion import RepositoryIngestor
from backend.main import app

client = TestClient(app)


def fake_runner_factory(fixture_path: Path):
    def fake_runner(args, timeout, cwd):
        dest = Path(args[-1])
        if dest.exists():
            import shutil

            shutil.rmtree(dest)
        import shutil as sh

        sh.copytree(fixture_path, dest)
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    return fake_runner


@pytest.fixture
def sample_repo_path():
    return Path(__file__).parent.parent / "fixtures" / "sample_repo"


class TestCodeAnalyzeEndpoint:
    def test_analyze_invalid_url(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={"repository_url": "not-a-url", "experiment_id": "1"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "REPOSITORY_VALIDATION_ERROR"

    def test_analyze_http_scheme_rejected(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={"repository_url": "http://github.com/owner/repo", "experiment_id": "1"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "UNSUPPORTED_REPOSITORY"

    def test_analyze_ssh_scheme_rejected(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={"repository_url": "git@github.com:owner/repo.git", "experiment_id": "1"},
        )
        assert response.status_code == 400
        assert response.json()["error"] in {"UNSUPPORTED_REPOSITORY", "REPOSITORY_VALIDATION_ERROR"}

    def test_analyze_credentials_rejected(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={
                "repository_url": "https://user:pass@github.com/owner/repo",
                "experiment_id": "1",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "REPOSITORY_VALIDATION_ERROR"

    def test_analyze_other_host_rejected(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={"repository_url": "https://gitlab.com/owner/repo", "experiment_id": "1"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "UNSUPPORTED_REPOSITORY"

    def test_analyze_missing_experiment_id(self):
        response = client.post(
            "/api/v1/code/analyze",
            json={"repository_url": "https://github.com/owner/repo"},
        )
        assert response.status_code == 422  # pydantic validation

    def test_analyze_nonexistent_experiment(self, sample_repo_path):
        with patch(
            "backend.code.service.RepositoryIngestor",
            return_value=RepositoryIngestor(runner=fake_runner_factory(sample_repo_path)),
        ):
            response = client.post(
                "/api/v1/code/analyze",
                json={"repository_url": "https://github.com/owner/repo", "experiment_id": "99999"},
            )
        assert response.status_code == 404
        assert response.json()["error"] == "EXPERIMENT_NOT_FOUND"


class TestRepositoryEndpoints:
    def test_get_nonexistent_repository(self):
        response = client.get("/api/v1/repository/99999")
        assert response.status_code == 404
        assert response.json()["error"] == "REPOSITORY_NOT_FOUND"

    def test_get_nonexistent_repository_files(self):
        response = client.get("/api/v1/repository/99999/files")
        assert response.status_code == 404

    def test_get_nonexistent_repository_mappings(self):
        response = client.get("/api/v1/repository/99999/mappings")
        assert response.status_code == 404

    def test_get_nonexistent_repository_readiness(self):
        response = client.get("/api/v1/repository/99999/readiness")
        assert response.status_code == 404


class TestExperimentCodeAnalysisEndpoint:
    def test_get_nonexistent_experiment_code_analysis(self):
        response = client.get("/api/v1/experiment/99999/code-analysis")
        assert response.status_code == 404
        assert response.json()["error"] == "EXPERIMENT_NOT_FOUND"


class TestFullAnalysisFlow:
    def test_analyze_with_valid_experiment_and_repo(self, sample_repo_path):
        # First create a paper and experiment via Part 1
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Batch size: 64 Learning rate: 0.001) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000117 00000 n
0000000216 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
310
%%EOF"""

        with patch(
            "backend.code.service.RepositoryIngestor",
            return_value=RepositoryIngestor(runner=fake_runner_factory(sample_repo_path)),
        ):
            # Upload paper
            paper_resp = client.post(
                "/api/v1/paper/analyze",
                files={"file": ("test.pdf", pdf_content, "application/pdf")},
            )
            assert paper_resp.status_code == 200
            paper_id = paper_resp.json()["paper_id"]
            # Get the actual experiment numeric ID by querying the paper's experiments
            exp_resp = client.get(f"/api/v1/paper/{paper_id}/experiments")
            assert exp_resp.status_code == 200
            exp_id = exp_resp.json()[0]["experiment_id"]

            # Analyze code
            code_resp = client.post(
                "/api/v1/code/analyze",
                json={
                    "repository_url": "https://github.com/owner/repo",
                    "paper_id": paper_id,
                    "experiment_id": exp_id,
                },
            )
            assert code_resp.status_code == 200, code_resp.text
            data = code_resp.json()

            # Verify response structure
            assert "repository" in data
            assert data["repository"]["owner"] == "owner"
            assert data["repository"]["name"] == "repo"
            assert data["experiment_id"] == exp_id
            assert "entry_points" in data
            assert len(data["entry_points"]) >= 1
            assert "code_parameters" in data
            assert "mappings" in data
            assert "readiness" in data

            # Check mappings - should have matched statuses for params present in PDF
            mappings = data["mappings"]
            mapping_map = {m["paper_field"]: m for m in mappings}
            for field in ["learning_rate", "batch_size"]:
                assert field in mapping_map, f"missing {field}"
                assert mapping_map[field]["status"] == "matched", (
                    f"{field}: {mapping_map[field]['status']}"
                )

            # Check readiness
            readiness = data["readiness"]
            assert "overall_score" in readiness
            assert "status" in readiness
            assert readiness["overall_score"] >= 0
            assert readiness["status"] in ["ready", "mostly_ready", "partial", "not_ready"]

            # Test GET endpoints
            repo_id = data["repository"]["id"]
            repo_resp = client.get(f"/api/v1/repository/{repo_id}")
            assert repo_resp.status_code == 200

            files_resp = client.get(f"/api/v1/repository/{repo_id}/files")
            assert files_resp.status_code == 200
            assert files_resp.json()["total"] >= 7

            mappings_resp = client.get(f"/api/v1/repository/{repo_id}/mappings")
            assert mappings_resp.status_code == 200

            readiness_resp = client.get(f"/api/v1/repository/{repo_id}/readiness")
            assert readiness_resp.status_code == 200

            exp_code_resp = client.get(f"/api/v1/experiment/{exp_id}/code-analysis")
            assert exp_code_resp.status_code == 200
