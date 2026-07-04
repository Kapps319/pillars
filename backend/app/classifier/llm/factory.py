"""Selects the LLM backend from LLM_PROVIDER, degrading gracefully to rules.

To add a new provider (e.g. a HuggingFace fine-tune), implement LLMClient in a
new module and add a branch here — nothing else in the codebase changes.
"""

from __future__ import annotations

from app.classifier.llm.base import LLMClient
from app.classifier.llm.claude_client import ClaudeClient
from app.classifier.llm.openai_client import OpenAIClient
from app.classifier.llm.rules_client import RulesOnlyClient
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_llm_client(settings: Settings | None = None, language: str = "en") -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider

    if provider == "claude":
        client = ClaudeClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model, language=language)
        if client.available():
            return client
        logger.warning("LLM_PROVIDER=claude but ANTHROPIC_API_KEY is missing — falling back to rules-only")
    elif provider == "openai":
        client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model, language=language)
        if client.available():
            return client
        logger.warning("LLM_PROVIDER=openai but OPENAI_API_KEY is missing — falling back to rules-only")

    return RulesOnlyClient(language=language)
