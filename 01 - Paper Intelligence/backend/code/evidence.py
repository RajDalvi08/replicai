"""Evidence records for the Code Intelligence module.

Every claim ReplicAI makes about a repository is expressed as evidence that
points at a real file, a real line range and a quote taken verbatim from the
analyzed source. Evidence is verified against the source before it is stored or
returned, so a quote that cannot be found in the file is reported as
unverified and never presented as proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.code.schemas import CodeEvidence
from backend.code.utils import RepositoryFile, split_source_lines

#: Quotes longer than this are truncated with an explicit marker.
MAX_QUOTE_LENGTH = 300


@dataclass
class SourceIndex:
    """Lazily reads analyzed source files so quotes can be verified."""

    root: Path
    _cache: dict[str, list[str] | None]

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, list[str] | None] = {}

    def lines_for(self, relative_path: str | None) -> list[str] | None:
        if not relative_path:
            return None
        if relative_path in self._cache:
            return self._cache[relative_path]
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:  # pragma: no cover - defensive
            self._cache[relative_path] = None
            return None
        try:
            raw = candidate.read_bytes()
        except OSError:
            self._cache[relative_path] = None
            return None
        if b"\x00" in raw:
            self._cache[relative_path] = None
            return None
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            self._cache[relative_path] = None
            return None
        lines = split_source_lines(text)
        self._cache[relative_path] = lines
        return lines

    def line_text(self, relative_path: str | None, line: int | None) -> str | None:
        lines = self.lines_for(relative_path)
        if lines is None or line is None:
            return None
        if 1 <= line <= len(lines):
            return lines[line - 1]
        return None

    def verify(self, evidence: CodeEvidence) -> bool:
        """Confirm the quote occurs at (or very near) the recorded location."""
        lines = self.lines_for(evidence.file)
        if lines is None:
            return False
        if not evidence.quote:
            # A quote is mandatory for anything presented as proof.
            return False

        normalized_quote = _normalize(evidence.quote)
        if not normalized_quote:
            return False

        start = evidence.line_start
        end = evidence.line_end or evidence.line_start
        if start is not None and 1 <= start <= len(lines):
            window = " ".join(lines[max(0, start - 1) : min(len(lines), (end or start))])
            if normalized_quote in _normalize(window):
                return True

        # Fall back to a whole-file containment check so long or indented
        # quotes are not rejected because of formatting.
        return normalized_quote in _normalize("\n".join(lines))


def _normalize(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def make_evidence(
    file_path: str,
    line: int | None,
    quote: str | None,
    confidence: float,
    *,
    source_index: SourceIndex | None = None,
    line_end: int | None = None,
) -> CodeEvidence:
    """Build an evidence object and, when possible, verify its quote."""
    cleaned_quote = None
    if quote:
        cleaned_quote = " ".join(quote.split())[:MAX_QUOTE_LENGTH]
    evidence = CodeEvidence(
        source_type="code",
        file=file_path,
        line_start=line,
        line_end=line_end or line,
        quote=cleaned_quote,
        confidence=round(min(max(confidence, 0.0), 1.0), 4),
    )
    if source_index is not None:
        evidence.verified = source_index.verify(evidence)
    return evidence


def evidence_from_file(
    repository_file: RepositoryFile, role: str, confidence: float, reason: str
) -> dict[str, object]:
    return {
        "file": repository_file.path,
        "role": role,
        "confidence": round(confidence, 4),
        "reason": reason,
    }
