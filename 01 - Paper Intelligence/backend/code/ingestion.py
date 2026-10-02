"""Safe repository ingestion.

Security contract enforced here:

* only validated ``https://github.com/owner/repo`` URLs reach git,
* git runs through a fixed argument list, ``shell=False``,
* a hard timeout is applied to every git invocation,
* the clone is shallow (depth 1, single branch, no tags),
* git is run with an environment that disables interactive credential prompts
  and system/global git configuration,
* the checkout lives in a private temporary directory that is always removed,
* repository code is never executed, imported or installed.
"""

from __future__ import annotations

import logging
import os
import subprocess  # nosec B404 - fixed git argument list, shell=False, timeout
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from backend.code.config import settings
from backend.code.exceptions import (
    RepositoryCloneError,
    RepositoryTooLargeError,
    UnsupportedRepositoryError,
)
from backend.code.utils import (
    NormalizedRepository,
    normalize_repository_url,
    safe_remove_tree,
)

logger = logging.getLogger("replicai.code.ingestion")

CommandRunner = Callable[[Sequence[str], int, Path], subprocess.CompletedProcess[str]]

DEFAULT_GIT_ENVIRONMENT: dict[str, str] = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "",
    "GCM_INTERACTIVE": "Never",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_ALLOW_PROTOCOL": "https",
    "GIT_PROTOCOL_FROM_USER": "0",
    "GIT_ADVICE": "0",
    "LC_ALL": "C",
}


def _default_runner(
    args: Sequence[str], timeout: int, cwd: Path
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603 B607 - fixed argv, shell=False, timeout
            list(args),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env=dict(DEFAULT_GIT_ENVIRONMENT),
        )
    except FileNotFoundError as exc:
        raise UnsupportedRepositoryError("git is not available on the analysis host.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepositoryCloneError("Repository clone exceeded the time limit.") from exc
    except OSError as exc:
        raise RepositoryCloneError("Repository clone could not be started.") from exc


@dataclass(frozen=True)
class IngestedRepository:
    """Metadata about a cloned repository. Source is deleted on context exit."""

    repository: NormalizedRepository
    workdir: Path
    commit_sha: str | None
    branch: str | None
    total_bytes: int
    elapsed_seconds: float

    def metadata(self) -> dict[str, str | int | None]:
        return {
            "repository_url": self.repository.normalized_url,
            "normalized_url": self.repository.normalized_url,
            "owner": self.repository.owner,
            "name": self.repository.name,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "total_bytes": self.total_bytes,
        }


def _directory_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for filename in files:
            try:
                total += (Path(root) / filename).stat().st_size
            except OSError:  # pragma: no cover - defensive
                continue
    return total


class RepositoryIngestor:
    """Clones a repository into a temporary directory and cleans it up."""

    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        max_bytes: int | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._runner: CommandRunner = runner or _default_runner
        self._max_bytes = max_bytes if max_bytes is not None else settings.max_repo_bytes
        self._timeout = (
            timeout_seconds if timeout_seconds is not None else settings.clone_timeout_seconds
        )

    # -- git helpers -------------------------------------------------------- #
    def _clone_arguments(self, target: NormalizedRepository, destination: Path) -> list[str]:
        arguments = [
            settings.git_executable,
            "-c",
            "protocol.ext.allow=never",
            "-c",
            "protocol.file.allow=never",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "credential.helper=",
            "clone",
            "--depth",
            str(settings.clone_depth),
            "--single-branch",
            "--no-tags",
            "--quiet",
            "--config",
            "advice.detachedHead=false",
        ]
        if target.branch:
            arguments.extend(["--branch", target.branch])
        arguments.extend([target.clone_url, str(destination)])
        return arguments

    def _read_head(self, workdir: Path) -> tuple[str | None, str | None]:
        commit: str | None = None
        branch: str | None = None
        try:
            result = self._runner(
                [
                    settings.git_executable,
                    "-C",
                    str(workdir),
                    "rev-parse",
                    "HEAD",
                ],
                int(self._timeout),
                workdir,
            )
            if result.returncode == 0:
                value = (result.stdout or "").strip()
                commit = value if 40 <= len(value) <= 64 else None

            branch_result = self._runner(
                [
                    settings.git_executable,
                    "-C",
                    str(workdir),
                    "rev-parse",
                    "--abbrev-ref",
                    "HEAD",
                ],
                int(self._timeout),
                workdir,
            )
            if branch_result.returncode == 0:
                value = (branch_result.stdout or "").strip()
                if value and value != "HEAD":
                    branch = value
        except (RepositoryCloneError, UnsupportedRepositoryError):  # pragma: no cover
            return commit, branch
        return commit, branch

    # -- public API --------------------------------------------------------- #
    def ingest(self, repository_url: str, branch: str | None = None) -> IngestedRepository:
        """Clone the repository. The caller owns the returned workdir cleanup."""
        target = normalize_repository_url(repository_url, branch)
        logger.info(
            "event=repository_ingestion_started host=%s owner=%s repo=%s",
            target.host,
            target.owner,
            target.name,
        )

        workdir = Path(tempfile.mkdtemp(prefix="replicai_repo_"))
        clone_target = workdir / "src"
        started = time.monotonic()
        try:
            arguments = self._clone_arguments(target, clone_target)
            result = self._runner(arguments, int(self._timeout), workdir)
            if result.returncode != 0:
                logger.warning(
                    "event=repository_clone_failed owner=%s repo=%s returncode=%s",
                    target.owner,
                    target.name,
                    result.returncode,
                )
                raise RepositoryCloneError(
                    "Repository could not be cloned. Verify that the repository "
                    "exists and is publicly accessible."
                )
            if not clone_target.is_dir():
                raise RepositoryCloneError("Repository clone produced no content.")

            total_bytes = _directory_size(clone_target)
            if total_bytes > self._max_bytes:
                logger.warning(
                    "event=repository_too_large owner=%s repo=%s bytes=%s",
                    target.owner,
                    target.name,
                    total_bytes,
                )
                raise RepositoryTooLargeError(
                    "Repository exceeds the configured analysis size limit."
                )

            commit_sha, detected_branch = self._read_head(clone_target)
            elapsed = round(time.monotonic() - started, 3)
            logger.info(
                "event=repository_cloned owner=%s repo=%s commit=%s bytes=%s elapsed=%ss",
                target.owner,
                target.name,
                commit_sha or "unknown",
                total_bytes,
                elapsed,
            )
            return IngestedRepository(
                repository=target,
                workdir=clone_target,
                commit_sha=commit_sha,
                branch=detected_branch or target.branch,
                total_bytes=total_bytes,
                elapsed_seconds=elapsed,
            )
        except BaseException:
            safe_remove_tree(workdir)
            raise

    def analyze(self, repository_url: str, branch: str | None = None) -> RepositoryWorkspace:
        return RepositoryWorkspace(self.ingest(repository_url, branch))


class RepositoryWorkspace:
    """Context manager guaranteeing deletion of the temporary checkout."""

    def __init__(self, ingested: IngestedRepository) -> None:
        self.ingested = ingested
        self._root = ingested.workdir.parent

    @property
    def root(self) -> Path:
        return self.ingested.workdir

    def __enter__(self) -> RepositoryWorkspace:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        safe_remove_tree(self._root)
        logger.info("event=repository_workspace_cleaned")
