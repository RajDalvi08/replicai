class PaperProcessingError(ValueError):
    code = "PAPER_PROCESSING_ERROR"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class InvalidPDFError(PaperProcessingError):
    code = "INVALID_PDF"


class LLMExtractionError(PaperProcessingError):
    code = "LLM_EXTRACTION_ERROR"
