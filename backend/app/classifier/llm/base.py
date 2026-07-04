"""Provider-agnostic LLM classifier interface (Stage 2).

Implementations: RulesOnlyClient (keyless default), ClaudeClient, OpenAIClient.
A HuggingFace/fine-tuned model is a drop-in: subclass LLMClient, implement
classify(), register it in factory.get_llm_client().
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.classifier.rules import RuleSignals
from app.core.config import CONFIG_DIR
from app.models.enums import IntentLabel


class ClassifyInput(BaseModel):
    text: str
    product: str | None = None
    location: str | None = None


class LLMResult(BaseModel):
    """Strict schema every provider must return; validated with Pydantic."""

    intent: IntentLabel
    confidence: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list, max_length=8)
    product: str | None = None
    price: float | None = None
    currency: str | None = None
    date: str | None = None
    location: str | None = None

    @field_validator("intent", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.upper() if isinstance(v, str) else v


class LLMError(Exception):
    """Raised when a provider fails; the pipeline degrades to rules-only."""


class LLMClient(ABC):
    name: str = "abstract"

    @abstractmethod
    def classify(self, inp: ClassifyInput, signals: RuleSignals) -> LLMResult:
        """Classify one post. Must raise LLMError on failure (never crash the app)."""

    def available(self) -> bool:
        return True


@lru_cache
def load_prompt(language: str = "en") -> dict:
    path: Path = CONFIG_DIR / "prompts" / f"classify_{language}.yml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def parse_llm_json(raw_text: str) -> LLMResult:
    """Parse + validate strict JSON output. Tolerates accidental markdown fences."""
    text = raw_text.strip()
    # Strip ```json fences if the model added them anyway
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # Last resort: grab the first {...} block
    if not text.startswith("{"):
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        return LLMResult.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMError(f"Malformed LLM output: {exc}") from exc
