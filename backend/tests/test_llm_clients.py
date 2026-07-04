from __future__ import annotations

import pytest

from app.classifier.llm.base import ClassifyInput, LLMError, parse_llm_json
from app.classifier.llm.factory import get_llm_client
from app.classifier.llm.rules_client import RulesOnlyClient
from app.classifier.rules import get_rules_engine
from app.core.config import Settings
from app.models.enums import IntentLabel


def test_parse_llm_json_plain():
    result = parse_llm_json('{"intent": "buy", "confidence": 88, "reasons": ["x"]}')
    assert result.intent == IntentLabel.BUY
    assert result.confidence == 88


def test_parse_llm_json_with_markdown_fences():
    result = parse_llm_json('```json\n{"intent": "SELL", "confidence": 70, "reasons": []}\n```')
    assert result.intent == IntentLabel.SELL


def test_parse_llm_json_malformed_raises():
    with pytest.raises(LLMError):
        parse_llm_json("sorry, I can't do that")
    with pytest.raises(LLMError):
        parse_llm_json('{"intent": "MAYBE", "confidence": 50, "reasons": []}')


def test_factory_defaults_to_rules():
    client = get_llm_client(Settings(llm_provider="rules"))
    assert isinstance(client, RulesOnlyClient)


def test_factory_falls_back_when_keys_missing():
    # LLM_PROVIDER=claude with no key must not crash — it degrades to rules
    client = get_llm_client(Settings(llm_provider="claude", anthropic_api_key=None))
    assert isinstance(client, RulesOnlyClient)
    client = get_llm_client(Settings(llm_provider="openai", openai_api_key=None))
    assert isinstance(client, RulesOnlyClient)


def test_factory_selects_claude_with_key():
    from app.classifier.llm.claude_client import ClaudeClient

    client = get_llm_client(Settings(llm_provider="claude", anthropic_api_key="sk-test"))
    assert isinstance(client, ClaudeClient)


def test_rules_client_shape():
    client = RulesOnlyClient()
    signals = get_rules_engine().analyze("WTB 2 tickets, budget $500, DM me, I'm in London")
    result = client.classify(ClassifyInput(text="WTB 2 tickets, budget $500, DM me, I'm in London"), signals)
    assert result.intent == IntentLabel.BUY
    assert result.price == 500.0
    assert result.location == "London"
