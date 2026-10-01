from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import settings
from backend.paper.exceptions import LLMExtractionError
from backend.paper.prompts import STRICT_EXTRACTION_PROMPT


class StructuredLLMAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model

    def is_configured(self) -> bool:
        return bool(self.api_key or self.base_url)

    def _parse_json(self, raw_text: str) -> dict[str, Any]:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:  # pragma: no cover - exercised by tests
            raise LLMExtractionError("Malformed LLM JSON response received.") from exc

        if not isinstance(data, dict):
            raise LLMExtractionError("LLM response was not a JSON object.")
        return data

    def _request(
        self, messages: list[dict[str, str]], *, retry: bool
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise LLMExtractionError("LLM configuration is not available.")

        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        if retry:
            payload["messages"].append(
                {
                    "role": "user",
                    "content": "Repair the previous malformed JSON and return valid JSON only.",
                }
            )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise LLMExtractionError(
                f"LLM request failed with status {response.status_code}."
            )

        payload_data = response.json()
        if "choices" not in payload_data or not payload_data["choices"]:
            raise LLMExtractionError("LLM response did not include any choices.")

        content = payload_data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def extract_experiments(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        prompt_context = {
            "pages": pages,
            "requirements": {
                "must_use_null_for_missing_values": True,
                "must_include_evidence": True,
                "must_preserve_page_numbers": True,
                "must_not_invent_unverified_values": True,
            },
        }
        messages = [
            {"role": "system", "content": STRICT_EXTRACTION_PROMPT},
            {"role": "user", "content": json.dumps(prompt_context, ensure_ascii=False)},
        ]

        for attempt in range(2):
            try:
                data = self._request(messages, retry=attempt > 0)
            except (LLMExtractionError, ValueError, TypeError, json.JSONDecodeError):
                if attempt == 1:
                    raise
                continue

            experiments = data.get("experiments")
            if not isinstance(experiments, list):
                if attempt == 1:
                    raise LLMExtractionError(
                        "LLM response did not contain an experiments list."
                    )
                continue
            return experiments

        raise LLMExtractionError("LLM extraction failed after one repair attempt.")
