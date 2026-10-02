"""Controlled application exceptions for the Code Intelligence module.

Every exception carries a stable machine readable ``code``. Messages are written
for API consumers: they never contain local filesystem paths, subprocess output,
credentials or environment values.
"""


class CodeIntelligenceError(ValueError):
    code = "CODE_INTELLIGENCE_ERROR"
    status_code = 400

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class RepositoryValidationError(CodeIntelligenceError):
    code = "REPOSITORY_VALIDATION_ERROR"


class UnsupportedRepositoryError(CodeIntelligenceError):
    code = "UNSUPPORTED_REPOSITORY"


class RepositoryCloneError(CodeIntelligenceError):
    code = "REPOSITORY_CLONE_ERROR"
    status_code = 502


class RepositoryTooLargeError(CodeIntelligenceError):
    code = "REPOSITORY_TOO_LARGE"


class RepositoryAnalysisError(CodeIntelligenceError):
    code = "REPOSITORY_ANALYSIS_ERROR"


class RepositoryNotFoundError(CodeIntelligenceError):
    code = "REPOSITORY_NOT_FOUND"
    status_code = 404


class ExperimentNotFoundError(CodeIntelligenceError):
    code = "EXPERIMENT_NOT_FOUND"
    status_code = 404


class CodeAnalysisTimeoutError(CodeIntelligenceError):
    code = "CODE_ANALYSIS_TIMEOUT"
    status_code = 504
