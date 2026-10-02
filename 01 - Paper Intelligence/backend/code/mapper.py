"""Paper to code mapping.

The Part 1 experiment is the expected specification. For every canonical
parameter this module decides one of five statuses:

``matched``
    Both sides carry a value and the values correspond.
``mismatched``
    Both sides carry a value and the values demonstrably differ.
``missing_in_code``
    The paper states a value but no reliable code value was detected.
``missing_in_paper``
    Code configures a value the paper does not state.
``uncertain``
    The available evidence is ambiguous or the values are not comparable.

Similar wording alone never produces ``matched``: numeric values are compared
numerically and textual values must normalize to the same identifier or to a
documented substring/token relationship.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.code.evidence import SourceIndex, make_evidence
from backend.code.parameters import (
    CANONICAL_PARAMETERS,
    NUMERIC_PARAMETERS,
    TEXTUAL_PARAMETERS,
    ParameterCandidate,
)
from backend.code.schemas import (
    MappingStatus,
    PaperEvidenceRef,
    ParameterMapping,
)
from backend.code.utils import coerce_to_number, normalize_identifier, normalize_text

logger = logging.getLogger("replicai.code.mapper")

#: Confidence assigned to statuses that are decisions about *absence*.
ABSENCE_CONFIDENCE = 0.6
#: Ceiling for a confident mismatch decision.
MISMATCH_CEILING = 0.95

#: Minimum token length required before a token match counts as evidence.
MIN_TOKEN_LENGTH = 4


@dataclass(frozen=True)
class ComparisonResult:
    matched: bool
    comparable: bool
    strength: float
    reason: str


def _tokens(value: str) -> list[str]:
    cleaned = normalize_text(value)
    for separator in ("_", "-", "/", ",", " "):
        cleaned = cleaned.replace(separator, " ")
    return [token for token in cleaned.split() if token]


def compare_values(paper_value: Any, code_value: Any, canonical_name: str) -> ComparisonResult:
    """Compare a paper value against a code value for one canonical parameter."""
    if paper_value is None or code_value is None:
        return ComparisonResult(False, False, 0.0, "value unavailable on one side")

    if canonical_name in NUMERIC_PARAMETERS:
        paper_number = coerce_to_number(paper_value)
        code_number = coerce_to_number(code_value)
        if paper_number is None or code_number is None:
            return ComparisonResult(
                False,
                False,
                0.0,
                f"non-numeric value for {canonical_name}: "
                f"paper={paper_value!r}, code={code_value!r}",
            )
        from backend.code.utils import values_are_numerically_close

        if values_are_numerically_close(float(paper_number), float(code_number)):
            return ComparisonResult(True, True, 1.0, f"numeric values are equal ({paper_number})")
        return ComparisonResult(
            False,
            True,
            0.0,
            f"numeric values differ (paper={paper_number}, code={code_number})",
        )

    if canonical_name in TEXTUAL_PARAMETERS:
        if not isinstance(paper_value, str) or not isinstance(code_value, str):
            return ComparisonResult(
                False,
                False,
                0.0,
                f"non-textual value for {canonical_name}: "
                f"paper={paper_value!r}, code={code_value!r}",
            )
        paper_norm = normalize_identifier(paper_value)
        code_norm = normalize_identifier(code_value)
        if not paper_norm or not code_norm:
            return ComparisonResult(False, False, 0.0, "identifier is not comparable")
        if paper_norm == code_norm:
            return ComparisonResult(
                True, True, 1.0, f"identifiers are equal after normalization ({paper_norm})"
            )
        if len(paper_norm) >= 3 and paper_norm in code_norm:
            return ComparisonResult(
                True,
                True,
                0.78,
                f"paper name '{paper_value}' is contained in code identifier '{code_value}'",
            )
        if len(code_norm) >= 3 and code_norm in paper_norm:
            return ComparisonResult(
                True,
                True,
                0.78,
                f"code name '{code_value}' is contained in paper name '{paper_value}'",
            )
        paper_tokens = [token for token in _tokens(paper_value) if len(token) >= MIN_TOKEN_LENGTH]
        code_tokens = {token for token in _tokens(code_value) if len(token) >= MIN_TOKEN_LENGTH}
        shared = {token for token in paper_tokens if token in code_tokens}
        if shared:
            return ComparisonResult(
                True,
                True,
                0.72,
                f"shared token(s) {sorted(shared)} between '{paper_value}' and '{code_value}'",
            )
        if _scheduler_related(paper_value, code_value):
            return ComparisonResult(
                True, True, 0.7, f"'{paper_value}' describes scheduler '{code_value}'"
            )
        return ComparisonResult(
            False,
            True,
            0.0,
            f"different identifiers (paper='{paper_value}', code='{code_value}')",
        )

    return ComparisonResult(False, False, 0.0, f"{canonical_name} is not a comparable parameter")


_SCHEDULER_TOKENS: dict[str, frozenset[str]] = {
    "StepLR": frozenset({"step", "step decay"}),
    "MultiStepLR": frozenset({"multi", "multistep", "step"}),
    "ExponentialLR": frozenset({"exponential", "exp"}),
    "CosineAnnealingLR": frozenset({"cosine", "cos"}),
    "CosineAnnealingWarmRestarts": frozenset({"cosine", "cos", "warm restart"}),
    "ReduceLROnPlateau": frozenset({"plateau", "reduce"}),
    "OneCycleLR": frozenset({"one cycle", "onecycle", "one-cycle"}),
    "LambdaLR": frozenset({"lambda"}),
    "CyclicLR": frozenset({"cyclic", "cycle"}),
    "LinearLR": frozenset({"linear"}),
    "PolynomialLR": frozenset({"polynomial", "poly"}),
}

_SCHEDULER_ALIASES: dict[str, frozenset[str]] = {
    "cosine": frozenset({"cosineannealinglr", "cosineannealingwarmrestarts"}),
    "step": frozenset({"steplr", "multisteplr", "multisteplrscheduler"}),
    "exponential": frozenset({"exponentiallr"}),
    "plateau": frozenset({"reducelronplateau"}),
    "onecycle": frozenset({"onecyclelr"}),
    "none": frozenset(),
    "constant": frozenset(),
    "linear": frozenset({"linearlr"}),
}


def _scheduler_related(paper_value: str, code_value: str) -> bool:
    """Relate a prose scheduler description to a scheduler class name."""
    paper_norm = normalize_identifier(paper_value)
    code_norm = normalize_identifier(code_value)
    if paper_norm in _SCHEDULER_ALIASES:
        return code_norm in _SCHEDULER_ALIASES[paper_norm]
    for code_name, tokens in _SCHEDULER_TOKENS.items():
        if normalize_identifier(code_name) != code_norm:
            continue
        normalized_tokens = {
            normalize_identifier(token) for token in tokens if normalize_identifier(token)
        }
        return bool(normalized_tokens & set(_tokens(paper_value)))
    return False


def _evidence_for(candidate: ParameterCandidate, source_index: SourceIndex | None):
    return make_evidence(
        candidate.file,
        candidate.line,
        candidate.quote,
        candidate.confidence,
        source_index=source_index,
    )


def _values_equal(left: Any, right: Any, canonical_name: str) -> bool:
    if left is None or right is None:
        return False
    return compare_values(left, right, canonical_name).matched


class PaperCodeMapper:
    """Compares Part 1 experiment parameters against detected code parameters."""

    def __init__(
        self,
        paper_parameters: dict[str, Any],
        code_candidates: dict[str, list[ParameterCandidate]],
        source_index: SourceIndex | None = None,
        paper_evidence: dict[str, list[PaperEvidenceRef]] | None = None,
    ) -> None:
        self._paper = paper_parameters
        self._code = code_candidates
        self._source_index = source_index
        self._paper_evidence = paper_evidence or {}

    def map_all(self) -> list[ParameterMapping]:
        mappings: list[ParameterMapping] = [
            self._map_parameter(name) for name in CANONICAL_PARAMETERS
        ]
        logger.info("event=mapping_completed mappings=%s", len(mappings))
        return mappings

    def _map_parameter(self, name: str) -> ParameterMapping:
        paper_value = self._paper.get(name)
        candidates = self._code.get(name, [])
        evidence_refs = self._paper_evidence.get(name, [])

        if not candidates and paper_value is None:
            return ParameterMapping(
                paper_field=name,
                paper_value=None,
                code_field=None,
                code_value=None,
                status=MappingStatus.missing_in_paper,
                confidence=ABSENCE_CONFIDENCE,
                reason="Neither the paper nor the code provides this parameter.",
                paper_evidence=evidence_refs,
            )

        if not candidates:
            return ParameterMapping(
                paper_field=name,
                paper_value=paper_value,
                code_field=None,
                code_value=None,
                status=MappingStatus.missing_in_code,
                confidence=ABSENCE_CONFIDENCE,
                reason=(
                    f"The paper states {name}={paper_value!r} but no reliable value "
                    "was detected in the repository."
                ),
                paper_evidence=evidence_refs,
            )

        primary = candidates[0]
        primary_evidence = _evidence_for(primary, self._source_index)
        conflicting = [
            candidate
            for candidate in candidates[1:]
            if candidate.priority == primary.priority
            and not _values_equal(candidate.value, primary.value, name)
        ]
        conflict_evidence = [
            _evidence_for(candidate, self._source_index) for candidate in conflicting[:3]
        ]

        if paper_value is None:
            reason = (
                f"The code configures {name}={primary.value!r} at "
                f"{primary.file}:{primary.line}, but the paper does not state it."
            )
            if conflict_evidence:
                reason += " Conflicting code values were also detected."
            return ParameterMapping(
                paper_field=name,
                paper_value=None,
                code_field=name,
                code_value=primary.value,
                status=(
                    MappingStatus.uncertain if conflict_evidence else MappingStatus.missing_in_paper
                ),
                confidence=(
                    round(0.3 * primary.confidence, 4) if conflict_evidence else ABSENCE_CONFIDENCE
                ),
                reason=reason,
                evidence=primary_evidence,
                conflicting_evidence=conflict_evidence,
                paper_evidence=evidence_refs,
            )

        comparison = compare_values(paper_value, primary.value, name)

        if not comparison.matched and comparison.comparable and not conflict_evidence:
            return ParameterMapping(
                paper_field=name,
                paper_value=paper_value,
                code_field=name,
                code_value=primary.value,
                status=MappingStatus.mismatched,
                confidence=round(min(MISMATCH_CEILING, 0.9 * primary.confidence), 4),
                reason=(f"{comparison.reason}; detected at {primary.file}:{primary.line}."),
                evidence=primary_evidence,
                paper_evidence=evidence_refs,
            )

        if not comparison.matched:
            return ParameterMapping(
                paper_field=name,
                paper_value=paper_value,
                code_field=name,
                code_value=primary.value,
                status=MappingStatus.uncertain,
                confidence=round(0.3 * primary.confidence, 4),
                reason=(f"{comparison.reason}; detected at {primary.file}:{primary.line}."),
                evidence=primary_evidence,
                conflicting_evidence=conflict_evidence,
                paper_evidence=evidence_refs,
            )

        if conflict_evidence:
            return ParameterMapping(
                paper_field=name,
                paper_value=paper_value,
                code_field=name,
                code_value=primary.value,
                status=MappingStatus.uncertain,
                confidence=round(0.45 * primary.confidence, 4),
                reason=(
                    f"{comparison.reason} at {primary.file}:{primary.line}, but "
                    "conflicting code values of equal evidence strength were detected."
                ),
                evidence=primary_evidence,
                conflicting_evidence=conflict_evidence,
                paper_evidence=evidence_refs,
            )

        return ParameterMapping(
            paper_field=name,
            paper_value=paper_value,
            code_field=name,
            code_value=primary.value,
            status=MappingStatus.matched,
            confidence=round(min(0.99, primary.confidence * comparison.strength), 4),
            reason=(f"{comparison.reason}; detected at {primary.file}:{primary.line}."),
            evidence=primary_evidence,
            paper_evidence=evidence_refs,
        )
