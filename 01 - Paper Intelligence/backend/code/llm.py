"""Optional LLM assist for the Code Intelligence module.

Rules that are not negotiable:

* the deterministic analysis is always produced and is never replaced,
* the LLM is only asked to *label* files that static analysis already found,
* the LLM may only reference file paths that exist in the analyzed repository,
* the LLM may not invent code locations, quotes or parameter values,
* any failure silently falls back to the deterministic result.

Because the adapter is optional, no test ever requires a live model.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from backend.code.config import settings
from backend.code.schemas import DetectedFile, FileRole

logger = logging.getLogger("replicai.code.llm")

ROLE_CLASSIFICATION_PROMPT = (
    "You label files in a research code repository. For each input file return a "
    "single JSON object with keys 'path', 'role' and 'confidence'. 'path' must be "
    "copied exactly from the input. 'role' must be one of: training_entrypoint, "
    "evaluation_entrypoint, inference_entrypoint, configuration, dataset, "
    "model_definition, optimizer, scheduler, metrics, documentation, "
    "dependency_manifest, unknown. Do not invent files and do not report line "
    "numbers or code. Return JSON only."
)

ROLES = tuple(role.value for role in FileRole)


class RoleSuggestion(BaseModel):
    path: str
    role: FileRole
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class RoleSuggestionList(BaseModel):
    suggestions: list[RoleSuggestion] = Field(default_factory=list)


class CodeLLMAdapter:
    """Thin wrapper around a chat-completions endpoint for file role labels."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        from backend.config import settings as app_settings

        self.api_key = api_key or app_settings.llm_api_key
        self.base_url = base_url or app_settings.llm_base_url
        self.model = model or app_settings.llm_model
        self.timeout = 20.0

    def is_configured(self) -> bool:
        return bool(settings.llm_enabled and (self.api_key or self.base_url))

    def _request(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        from backend.config import settings as app_settings

        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ROLE_CLASSIFICATION_PROMPT},
                {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise ValueError(f"LLM request failed with status {response.status_code}.")
        payload = response.json()
        if not payload.get("choices"):
            raise ValueError("LLM response did not include any choices.")
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response was not a JSON object.")
        del app_settings
        return parsed

    def suggest_roles(self, files: list[DetectedFile]) -> dict[str, RoleSuggestion]:
        """Return validated role suggestions keyed by known file path."""
        if not self.is_configured() or not files:
            return {}
        candidates = [
            {"path": item.path, "detected_role": item.role.value, "confidence": item.confidence}
            for item in files
            if item.role is FileRole.unknown and item.confidence < 0.6
        ]
        if not candidates:
            return {}
        try:
            raw = self._request({"files": candidates})
            parsed = RoleSuggestionList.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 - LLM output is untrusted
            logger.info("event=llm_role_classification_skipped reason=%s", type(exc).__name__)
            return {}

        known_paths = {item.path for item in files}
        suggestions: dict[str, RoleSuggestion] = {}
        for suggestion in parsed.suggestions:
            if suggestion.path not in known_paths:
                # Reject any hallucinated path.
                continue
            if suggestion.role.value not in ROLES:  # pragma: no cover - pydantic guards
                continue
            if suggestion.confidence < 0.5:
                continue
            suggestions[suggestion.path] = suggestion
        if suggestions:
            logger.info("event=llm_role_suggestions_used count=%s", len(suggestions))
        return suggestions


def merge_llm_role_suggestions(
    files: list[DetectedFile], suggestions: dict[str, RoleSuggestion]
) -> list[DetectedFile]:
    """Apply suggestions only where static evidence was weak.

    Static analysis always wins: a suggestion can only upgrade a file that was
    previously classified as ``unknown``, and the resulting confidence is capped
    below the deterministic threshold used for strongly supported roles.
    """
    if not suggestions:
        return files
    merged: list[DetectedFile] = []
    for item in files:
        suggestion = suggestions.get(item.path)
        if suggestion is None or item.role is not FileRole.unknown:
            merged.append(item)
            continue
        merged.append(
            item.model_copy(
                update={
                    "role": suggestion.role,
                    "confidence": min(0.5, suggestion.confidence),
                    "evidence": item.evidence
                    + [f"LLM role suggestion: {suggestion.reason or 'labelled'}"],
                }
            )
        )
    return merged
