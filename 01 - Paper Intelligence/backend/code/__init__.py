"""Code Intelligence package for ReplicAI (Part 2).

The module statically analyzes an untrusted GitHub repository, maps the
parameters extracted from a research paper (Part 1) onto the values that are
actually configured in code, and produces a deterministic readiness score.

Repository code is statically analyzed and never executed.
"""

from backend.code.exceptions import (
    CodeAnalysisTimeoutError,
    CodeIntelligenceError,
    ExperimentNotFoundError,
    RepositoryAnalysisError,
    RepositoryCloneError,
    RepositoryNotFoundError,
    RepositoryTooLargeError,
    RepositoryValidationError,
    UnsupportedRepositoryError,
)

__all__ = [
    "CodeAnalysisTimeoutError",
    "CodeIntelligenceError",
    "ExperimentNotFoundError",
    "RepositoryAnalysisError",
    "RepositoryCloneError",
    "RepositoryNotFoundError",
    "RepositoryTooLargeError",
    "RepositoryValidationError",
    "UnsupportedRepositoryError",
]
