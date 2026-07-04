"""OpenAIClient — alternative LLM provider via the Chat Completions HTTP API.

Requires OPENAI_API_KEY (set LLM_PROVIDER=openai to activate). Enforces JSON
output via response_format, validates with Pydantic, retries once.
"""

from __future__ import annotations

import httpx

from app.classifier.llm.base import ClassifyInput, LLMClient, LLMError, LLMResult, load_prompt, parse_llm_json
from app.classifier.rules import RuleSignals
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIClient(LLMClient):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None, language: str = "en"):
        settings = get_settings()
        # OPENAI_API_KEY is required for this client — the factory falls back
        # to RulesOnlyClient when it's missing.
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.openai_model
        self._prompt = load_prompt(language)

    def available(self) -> bool:
        return bool(self._api_key)

    @property
    def model_id(self) -> str:
        return f"openai:{self._model}"

    def classify(self, inp: ClassifyInput, signals: RuleSignals) -> LLMResult:
        if not self.available():
            raise LLMError("OPENAI_API_KEY not configured")
        user_msg = self._prompt["user_template"].format(
            product=inp.product or "(any)", location=inp.location or "(any)", text=inp.text
        )
        messages = [
            {"role": "system", "content": self._prompt["system"]},
            {"role": "user", "content": user_msg},
        ]
        try:
            raw = self._call(messages)
            try:
                return parse_llm_json(raw)
            except LLMError:
                logger.warning("OpenAI returned malformed JSON; retrying once")
                messages.append({"role": "assistant", "content": raw[:2000]})
                messages.append({"role": "user", "content": self._prompt["retry_nudge"]})
                return parse_llm_json(self._call(messages))
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"OpenAI API call failed: {exc}") from exc

    def _call(self, messages: list[dict]) -> str:
        response = httpx.post(
            _API_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "max_tokens": 1024,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not content:
            raise LLMError("Empty response from OpenAI")
        return content
