"""Tests for the Code Intelligence module - evidence verification."""

from pathlib import Path

from backend.code.evidence import SourceIndex, make_evidence
from backend.code.schemas import CodeEvidence


def test_source_index_verification(sample_repo_path: Path):
    index = SourceIndex(sample_repo_path)

    # Valid quote from train.py
    lines = index.lines_for("train.py")
    assert lines is not None
    assert len(lines) > 0

    # Verify a real quote
    evidence = CodeEvidence(
        source_type="code",
        file="train.py",
        line_start=1,
        line_end=1,
        quote="import argparse",
        confidence=0.9,
    )
    assert index.verify(evidence) is True

    # Invalid quote (not in file)
    evidence2 = CodeEvidence(
        source_type="code",
        file="train.py",
        line_start=1,
        line_end=1,
        quote="this quote does not exist anywhere",
        confidence=0.9,
    )
    assert index.verify(evidence2) is False

    # Wrong file
    evidence3 = CodeEvidence(
        source_type="code",
        file="nonexistent.py",
        line_start=1,
        line_end=1,
        quote="anything",
        confidence=0.9,
    )
    assert index.verify(evidence3) is False

    # Missing quote
    evidence4 = CodeEvidence(
        source_type="code",
        file="train.py",
        line_start=1,
        line_end=1,
        quote=None,
        confidence=0.9,
    )
    assert index.verify(evidence4) is False


def test_make_evidence(sample_repo_path: Path):
    index = SourceIndex(sample_repo_path)
    evidence = make_evidence("train.py", 1, "import argparse", 0.95, source_index=index)
    assert evidence.verified is True
    assert evidence.file == "train.py"
    assert evidence.line_start == 1
    assert evidence.quote == "import argparse"


def test_evidence_truncation(sample_repo_path: Path):
    index = SourceIndex(sample_repo_path)
    long_quote = "x" * 500
    evidence = make_evidence("train.py", 1, long_quote, 0.9, source_index=index)
    assert len(evidence.quote) <= 300
