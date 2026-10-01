from __future__ import annotations

from typing import Any


def verify_quote_in_text(quote: str | None, text: str | None) -> bool:
    if not quote or not text:
        return False

    normalized_text = " ".join(text.lower().split())
    normalized_quote = " ".join(quote.lower().split())
    return normalized_quote in normalized_text


def validate_evidence(
    evidence: dict[str, Any],
    page_count: int,
    page_texts: dict[int, str],
) -> dict[str, Any]:
    issues: list[str] = []
    page = evidence.get("page")

    if page is None:
        issues.append("Evidence is missing a page reference.")
    elif page < 1 or page > page_count:
        issues.append("Evidence page is outside the PDF page count.")

    quote = evidence.get("quote")
    if page is not None:
        page_text = page_texts.get(page, "")
        if quote and page_text and not verify_quote_in_text(str(quote), page_text):
            issues.append("Evidence quote could not be verified in the page text.")

    field = evidence.get("field")
    value = evidence.get("value")
    if field is not None and value is None:
        issues.append(f"Evidence for field '{field}' is missing a value.")

    if field and not isinstance(field, str):
        issues.append("Evidence field name must be a string.")

    return {"valid": not issues, "issues": issues}
