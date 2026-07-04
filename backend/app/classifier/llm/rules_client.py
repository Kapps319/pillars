"""RulesOnlyClient — the keyless default.

Wraps the Stage-1 rules verdict plus deterministic extraction in the same
LLMResult shape as the real LLM providers, so the rest of the pipeline never
cares which backend produced the classification.
"""

from __future__ import annotations

from app.classifier import extraction
from app.classifier.llm.base import ClassifyInput, LLMClient, LLMResult
from app.classifier.rules import RuleSignals, get_rules_engine


class RulesOnlyClient(LLMClient):
    name = "rules"

    def __init__(self, language: str = "en"):
        self._engine = get_rules_engine(language)

    def classify(self, inp: ClassifyInput, signals: RuleSignals) -> LLMResult:
        label, confidence, reasons = self._engine.preliminary_label(signals)
        price, currency = extraction.extract_price(inp.text)
        return LLMResult(
            intent=label,
            confidence=confidence,
            reasons=reasons,
            product=extraction.extract_product(inp.text, inp.product),
            price=price,
            currency=currency,
            date=extraction.extract_date(inp.text),
            location=extraction.extract_location(inp.text, self._engine.locations, inp.location),
        )
