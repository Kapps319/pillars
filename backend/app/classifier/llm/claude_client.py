"""ClaudeClient — Anthropic API implementation of the LLMClient interface.

Requires ANTHROPIC_API_KEY (set LLM_PROVIDER=claude to activate). Uses the
official `anthropic` SDK. Output is strict JSON validated with Pydantic and
retried once with a corrective nudge on malformed output.
"""

from __future__ import annotations

from app.classifier.llm.base import ClassifyInput, LLMClient, LLMError, LLMResult, load_prompt, parse_llm_json
from app.classifier.rules import RuleSignals
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClaudeClient(LLMClient):
    name = "claude"

    def __init__(self, api_key: str | None = None, model: str | None = None, language: str = "en"):
        settings = get_settings()
        # ANTHROPIC_API_KEY is required for this client — the factory falls
        # back to RulesOnlyClient when it's missing.
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.anthropic_model
        self._prompt = load_prompt(language)
        self._client = None

    def available(self) -> bool:
        return bool(self._api_key)

    def _sdk_client(self):
        if self._client is None:
            import anthropic  # imported lazily so the app boots even if unused

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    @property
    def model_id(self) -> str:
        return f"claude:{self._model}"

    def classify(self, inp: ClassifyInput, signals: RuleSignals) -> LLMResult:
        if not self.available():
            raise LLMError("ANTHROPIC_API_KEY not configured")
        user_msg = self._prompt["user_template"].format(
            product=inp.product or "(any)", location=inp.location or "(any)", text=inp.text
        )
        messages = [{"role": "user", "content": user_msg}]
        try:
            raw = self._call(messages)
            try:
                return parse_llm_json(raw)
            except LLMError:
                # Retry exactly once with a corrective nudge
                logger.warning("Claude returned malformed JSON; retrying once")
                messages = [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": raw[:2000]},
                    {"role": "user", "content": self._prompt["retry_nudge"]},
                ]
                return parse_llm_json(self._call(messages))
        except LLMError:
            raise
        except Exception as exc:  # network errors, rate limits, refusals...
            raise LLMError(f"Anthropic API call failed: {exc}") from exc

    def _call(self, messages: list[dict]) -> str:
        response = self._sdk_client().messages.create(
            model=self._model,
            max_tokens=1024,
            system=self._prompt["system"],
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise LLMError("Claude declined to classify this post (refusal)")
        text = "".join(block.text for block in response.content if block.type == "text")
        if not text:
            raise LLMError("Empty response from Claude")
        return text
