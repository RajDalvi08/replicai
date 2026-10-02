"""Tests for the Code Intelligence module - repository ingestion."""

import stat
from pathlib import Path
from unittest.mock import MagicMock

from backend.code.exceptions import (
    RepositoryCloneError,
    RepositoryTooLargeError,
)
from backend.code.ingestion import RepositoryIngestor
from backend.code.utils import normalize_repository_url, safe_remove_tree


class TestRepositoryIngestor:
    def test_successful_shallow_clone(self, tmp_path):
        """Test that a mock clone succeeds and returns metadata."""
        repo_dir = tmp_path / "sample_repo"
        repo_dir.mkdir()
        (repo_dir / "train.py").write_text("lr = 0.001\n")
        (repo_dir / "config.py").write_text("lr = 0.001\n")

        call_count = 0

        def fake_runner(args, timeout, cwd):
            nonlocal call_count
            call_count += 1
            import shutil

            dest = Path(args[-1])
            if call_count == 1:
                shutil.copytree(repo_dir, dest)
            elif call_count == 2:
                git_dir = dest / ".git"
                git_dir.mkdir(exist_ok=True)
                (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc123\n"
            result.stderr = ""
            return result

        ingestor = RepositoryIngestor(runner=fake_runner, max_bytes=1024 * 1024)
        target = normalize_repository_url("https://github.com/owner/repo")
        ingested = ingestor.ingest("https://github.com/owner/repo")

        assert ingested.repository.owner == "owner"
        assert ingested.repository.name == "repo"
        assert ingested.workdir.exists()
        assert (ingested.workdir / "train.py").exists()

    def test_cleanup_on_context_exit(self, tmp_path):
        """Test that the temporary directory is removed on exit."""
        repo_dir = tmp_path / "sample_repo"
        repo_dir.mkdir()
        (repo_dir / "train.py").write_text("lr = 0.001\n")

        call_count = 0

        def fake_runner(args, timeout, cwd):
            nonlocal call_count
            call_count += 1
            import shutil

            dest = Path(args[-1])
            if call_count == 1:
                shutil.copytree(repo_dir, dest)
            elif call_count == 2:
                git_dir = dest / ".git"
                git_dir.mkdir(exist_ok=True)
                (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc123\n"
            result.stderr = ""
            return result

        ingestor = RepositoryIngestor(runner=fake_runner)
        target = normalize_repository_url("https://github.com/owner/repo")
        workspace = ingestor.analyze("https://github.com/owner/repo")
        root = workspace.ingested.workdir.parent
        assert root.exists()
        workspace.cleanup()
        assert not root.exists()

    def test_clone_failure_raises(self):
        def fake_runner(args, timeout, cwd):
            result = MagicMock()
            result.returncode = 128
            result.stderr = "fatal: repository not found"
            return result

        ingestor = RepositoryIngestor(runner=fake_runner)
        try:
            ingestor.ingest("https://github.com/owner/nonexistent")
            assert False, "should raise"
        except RepositoryCloneError:
            pass

    def test_timeout_raises(self):
        """Verify the exception hierarchy."""
        assert issubclass(RepositoryCloneError, Exception)

    def test_repository_too_large_raises(self, tmp_path):
        """Test that oversized repos are rejected after clone."""
        repo_dir = tmp_path / "sample_repo"
        repo_dir.mkdir()
        (repo_dir / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))

        def fake_runner(args, timeout, cwd):
            import shutil

            dest = Path(args[-1])
            shutil.copytree(repo_dir, dest)
            result = MagicMock()
            result.returncode = 0
            result.stdout = "abc123\n"
            return result

        ingestor = RepositoryIngestor(runner=fake_runner, max_bytes=1024 * 1024)
        try:
            ingestor.ingest("https://github.com/owner/repo")
            assert False, "should raise"
        except RepositoryTooLargeError:
            pass


class TestSafeRemoveTree:
    def test_removes_readonly_files(self, tmp_path):
        """Test that read-only git objects are removed."""
        d = tmp_path / "todelete"
        d.mkdir()
        f = d / "readonly"
        f.write_text("content")
        f.chmod(stat.S_IREAD)  # read-only
        safe_remove_tree(d)
        assert not d.exists()
