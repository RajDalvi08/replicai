"""Tests for the Code Intelligence module - URL validation."""

from backend.code.exceptions import (
    RepositoryValidationError,
    UnsupportedRepositoryError,
)
from backend.code.utils import normalize_branch, normalize_repository_url


class TestNormalizeRepositoryUrl:
    def test_valid_github_https(self):
        result = normalize_repository_url("https://github.com/owner/repo")
        assert result.owner == "owner"
        assert result.name == "repo"
        assert result.normalized_url == "https://github.com/owner/repo"
        assert result.clone_url == "https://github.com/owner/repo.git"
        assert result.branch is None

    def test_valid_with_git_suffix(self):
        result = normalize_repository_url("https://github.com/owner/repo.git")
        assert result.name == "repo"

    def test_valid_with_trailing_slash(self):
        result = normalize_repository_url("https://github.com/owner/repo/")
        assert result.name == "repo"

    def test_valid_with_branch_tree_path(self):
        result = normalize_repository_url("https://github.com/owner/repo/tree/main")
        assert result.branch == "main"

    def test_valid_with_branch_blob_path(self):
        result = normalize_repository_url("https://github.com/owner/repo/blob/develop/src/file.py")
        assert result.branch == "develop/src/file.py"

    def test_invalid_empty_url(self):
        try:
            normalize_repository_url("")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_http_scheme(self):
        try:
            normalize_repository_url("http://github.com/owner/repo")
            assert False, "should raise"
        except UnsupportedRepositoryError:
            pass

    def test_invalid_ssh_url(self):
        try:
            normalize_repository_url("git@github.com:owner/repo.git")
            assert False, "should raise"
        except (UnsupportedRepositoryError, RepositoryValidationError):
            pass

    def test_invalid_git_protocol(self):
        try:
            normalize_repository_url("git://github.com/owner/repo")
            assert False, "should raise"
        except UnsupportedRepositoryError:
            pass

    def test_invalid_credentials(self):
        try:
            normalize_repository_url("https://user:pass@github.com/owner/repo")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_control_chars(self):
        try:
            normalize_repository_url("https://github.com/owner/repo\x00")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_path_traversal(self):
        try:
            normalize_repository_url("https://github.com/owner/../repo")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_query_fragment(self):
        try:
            normalize_repository_url("https://github.com/owner/repo?foo=bar")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_other_host(self):
        try:
            normalize_repository_url("https://gitlab.com/owner/repo")
            assert False, "should raise"
        except UnsupportedRepositoryError:
            pass

    def test_invalid_malformed_path(self):
        try:
            normalize_repository_url("https://github.com/owner")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_starts_with_dash(self):
        try:
            normalize_repository_url("-https://github.com/owner/repo")
            assert False, "should raise"
        except RepositoryValidationError:
            pass


class TestNormalizeBranch:
    from backend.code.utils import normalize_branch

    def test_none_returns_none(self):
        assert normalize_branch(None) is None

    def test_empty_returns_none(self):
        assert normalize_branch("") is None

    def test_valid_branch(self):
        assert normalize_branch("main") == "main"
        assert normalize_branch("feature/new-stuff") == "feature/new-stuff"
        assert normalize_branch("v1.2.3") == "v1.2.3"

    def test_invalid_starts_with_dash(self):
        try:
            normalize_branch("-bad")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_double_dot(self):
        try:
            normalize_branch("bad..branch")
            assert False, "should raise"
        except RepositoryValidationError:
            pass

    def test_invalid_lock_suffix(self):
        try:
            normalize_branch("branch.lock")
            assert False, "should raise"
        except RepositoryValidationError:
            pass
