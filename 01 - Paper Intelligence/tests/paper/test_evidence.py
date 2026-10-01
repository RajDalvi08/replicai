from backend.paper.evidence import validate_evidence, verify_quote_in_text


def test_validate_evidence_page_ok():
    evidence = {
        "field": "batch_size",
        "value": 64,
        "page": 7,
        "source_type": "table",
        "source_label": "Table 3",
        "quote": "Batch size 64",
        "confidence": 0.96,
    }
    result = validate_evidence(
        evidence, page_count=12, page_texts={7: "Experimental Setup\nBatch size 64"}
    )
    assert result["valid"] is True


def test_validate_evidence_page_bad():
    evidence = {
        "field": "batch_size",
        "value": 64,
        "page": 42,
        "source_type": "table",
        "source_label": "Table 3",
        "quote": "Batch size 64",
        "confidence": 0.96,
    }
    result = validate_evidence(
        evidence, page_count=12, page_texts={7: "Experimental Setup\nBatch size 64"}
    )
    assert result["valid"] is False
    assert "page" in result["issues"][0].lower()


def test_quote_verification_detects_missing_quote():
    text = "Experimental Setup\nBatch size 32"
    result = verify_quote_in_text("Batch size 64", text)
    assert result is False
