"""Utilities for the Code Intelligence module.

Contains:

* strict GitHub HTTPS repository URL validation and normalization,
* safe, bounded repository file walking with ignore rules,
* small text/similarity helpers used by mapping and evidence verification.

Nothing in this module executes, imports or evaluates repository code.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from backend.code.config import (
    IGNORED_DIRECTORY_NAMES,
    IGNORED_FILE_SUFFIXES,
    settings,
)
from backend.code.exceptions import (
    RepositoryTooLargeError,
    RepositoryValidationError,
    UnsupportedRepositoryError,
)

# --------------------------------------------------------------------------- #
# URL validation / normalization
# --------------------------------------------------------------------------- #
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_ALLOWED_URL_CHARS_RE = re.compile(r"^[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")
# A git ref that we may safely pass to ``git clone --branch``.
_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")

_OWNER_RESERVED = {"-", "--config", "-c", "--upload-pack"}


@dataclass(frozen=True)
class NormalizedRepository:
    owner: str
    name: str
    host: str
    normalized_url: str
    clone_url: str
    branch: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


def normalize_branch(branch: str | None) -> str | None:
    """Validate an optional branch/ref before it reaches a git argument list."""
    if branch is None:
        return None
    cleaned = branch.strip()
    if not cleaned:
        return None
    if cleaned.startswith("-"):
        raise RepositoryValidationError("Branch name is not allowed to start with '-'.")
    if cleaned.endswith(".lock") or ".." in cleaned:
        raise RepositoryValidationError("Branch name is not a valid git reference.")
    if not _BRANCH_RE.match(cleaned):
        raise RepositoryValidationError("Branch name contains unsupported characters.")
    return cleaned


def normalize_repository_url(url: str, branch: str | None = None) -> NormalizedRepository:
    """Validate and normalize a public GitHub HTTPS repository URL.

    Only ``https://github.com/owner/repo`` style URLs are accepted. Anything
    else (other protocols, other hosts, embedded credentials, git options,
    nested paths, IP literals) is rejected before any subprocess is created.
    """
    if not isinstance(url, str):  # pragma: no cover - guarded by pydantic
        raise RepositoryValidationError("Repository URL must be a string.")

    candidate = url.strip()
    if not candidate:
        raise RepositoryValidationError("Repository URL must not be empty.")
    if len(candidate) > 2048:
        raise RepositoryValidationError("Repository URL is too long.")
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        raise RepositoryValidationError("Repository URL contains control characters.")
    if not _ALLOWED_URL_CHARS_RE.match(candidate):
        raise RepositoryValidationError("Repository URL contains unsupported characters.")
    if ".." in candidate:
        raise RepositoryValidationError("Repository URL contains a path traversal.")
    if candidate.startswith("-"):
        raise RepositoryValidationError("Repository URL is not allowed to start with '-'.")

    try:
        parts = urlsplit(candidate)
    except ValueError as exc:  # pragma: no cover - urlsplit rarely raises
        raise RepositoryValidationError("Repository URL could not be parsed.") from exc

    scheme = (parts.scheme or "").lower()
    if not scheme:
        raise RepositoryValidationError("Repository URL must include https://")
    if scheme not in settings.allowed_schemes:
        raise UnsupportedRepositoryError("Only https:// repository URLs are supported.")
    if parts.username or parts.password or "@" in parts.netloc:
        raise RepositoryValidationError("Repository URL must not embed credentials.")
    if parts.query or parts.fragment:
        raise RepositoryValidationError("Repository URL must not contain a query or fragment.")

    host = (parts.hostname or "").lower()
    if not host:
        raise RepositoryValidationError("Repository URL must include a host.")
    if host not in settings.allowed_hosts:
        raise UnsupportedRepositoryError(
            "Only GitHub repositories are supported by this prototype."
        )

    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) < 2:
        raise RepositoryValidationError(
            "Repository URL must look like https://github.com/owner/repository."
        )

    owner = segments[0]
    name = segments[1]
    name = name.removesuffix(".git")

    if not _OWNER_RE.match(owner) or owner.lower() in _OWNER_RESERVED:
        raise RepositoryValidationError("Repository owner segment is not valid.")
    if not _REPO_RE.match(name) or name in {".", ".."}:
        raise RepositoryValidationError("Repository name segment is not valid.")

    # Tolerate the browser-style deep links users paste from the GitHub UI.
    remainder = segments[2:]
    detected_branch: str | None = None
    if remainder:
        if remainder[0] in {"tree", "blob"} and len(remainder) >= 2:
            detected_branch = normalize_branch("/".join(remainder[1:]))
        else:
            raise RepositoryValidationError("Repository URL must point at the repository root.")

    selected_branch = normalize_branch(branch) or detected_branch
    normalized_url = f"https://{host}/{owner}/{name}"
    clone_url = f"{normalized_url}.git"
    return NormalizedRepository(
        owner=owner,
        name=name,
        host=host,
        normalized_url=normalized_url,
        clone_url=clone_url,
        branch=selected_branch,
    )


# --------------------------------------------------------------------------- #
# Bounded repository walking
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RepositoryFile:
    path: str
    absolute_path: Path
    size_bytes: int
    suffix: str

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    @property
    def depth(self) -> int:
        return len(PurePosixPath(self.path).parts)


def is_ignored_directory(name: str) -> bool:
    return name.lower() in IGNORED_DIRECTORY_NAMES


def is_ignored_file(path: PurePosixPath) -> bool:
    lowered = path.name.lower()
    if any(lowered.endswith(suffix) for suffix in IGNORED_FILE_SUFFIXES):
        return True
    if lowered.startswith("."):
        return True
    return False


def iter_repository_files(root: Path) -> Iterator[RepositoryFile]:
    """Yield non-ignored files below ``root`` in a deterministic order.

    The walk is depth limited, never follows symlinks and never raises for
    unreadable entries; those are reported as skipped by the caller.
    """
    root = root.resolve()
    max_depth = settings.max_depth
    max_file_bytes = settings.max_file_bytes

    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        if depth > max_depth:
            continue
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except (OSError, PermissionError):  # pragma: no cover - defensive
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if is_ignored_directory(entry.name):
                        continue
                    stack.append((entry, depth + 1))
                    continue
                if not entry.is_file():
                    continue
            except OSError:  # pragma: no cover - defensive
                continue

            relative = entry.relative_to(root).as_posix()
            pure = PurePosixPath(relative)
            if is_ignored_file(pure):
                continue
            try:
                size = entry.stat().st_size
            except OSError:  # pragma: no cover - defensive
                continue
            if size > max_file_bytes:
                continue
            yield RepositoryFile(
                path=relative,
                absolute_path=entry,
                size_bytes=size,
                suffix=pure.suffix.lower(),
            )


def collect_repository_files(root: Path) -> list[RepositoryFile]:
    """Collect files, enforcing the total file-count and total size limits."""
    collected: list[RepositoryFile] = []
    total_bytes = 0
    for candidate in iter_repository_files(root):
        total_bytes += candidate.size_bytes
        if total_bytes > settings.max_repo_bytes:
            raise RepositoryTooLargeError("Repository content exceeds the configured size limit.")
        collected.append(candidate)
        if len(collected) > settings.max_file_count:
            raise RepositoryTooLargeError(
                "Repository contains more files than the configured limit."
            )
    collected.sort(key=lambda item: item.path)
    return collected


def read_text_file(path: Path, *, max_bytes: int | None = None) -> str | None:
    """Read a text file defensively. Binary or oversized files yield ``None``."""
    limit = max_bytes if max_bytes is not None else settings.max_file_bytes
    try:
        if path.stat().st_size > limit:
            return None
        raw = path.read_bytes()
    except OSError:  # pragma: no cover - defensive
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive
            return None


def split_source_lines(text: str) -> list[str]:
    """Split source text into lines, collapsing illegal characters."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        if len(raw_line) > settings.max_file_line_length:
            raw_line = raw_line[: settings.max_file_line_length]
        lines.append(unicodedata.normalize("NFKC", raw_line).rstrip())
    return lines


def source_snippet(lines: list[str], line_number: int) -> str | None:
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    return None


# --------------------------------------------------------------------------- #
# Normalization helpers used by parameter normalization and mapping
# --------------------------------------------------------------------------- #
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_identifier(value: str) -> str:
    """Lowercase, de-punctuate and collapse an identifier into comparable form."""
    lowered = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return _NON_ALNUM_RE.sub("", lowered.replace("_", ""))


def normalize_text(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def values_are_numerically_close(left: float, right: float) -> bool:
    return abs(left - right) <= max(1e-12, 1e-9 * max(abs(left), abs(right)))


def coerce_to_number(value: object) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.strip().replace("_", "").replace(",", "")
        try:
            return int(cleaned)
        except ValueError:
            pass
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def safe_remove_tree(path: Path) -> None:
    """Remove a temporary directory, clearing read-only git object files."""
    if not path.exists():
        return

    def _on_error(func, target, _exc_info) -> None:  # type: ignore[no-untyped-def]
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:  # pragma: no cover - best effort cleanup
            pass

    shutil.rmtree(path, onerror=_on_error)


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output
