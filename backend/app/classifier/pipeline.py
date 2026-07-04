"""The full 3-stage classification pipeline.

Stage 1: rules filter (regex/keyword signals, spam/noise pre-filter)
Stage 2: LLM classifier behind the LLMClient interface (rules-only by default)
Stage 3: deterministic extraction + weighted scoring + reason tags

Every LLM failure degrades gracefully to the rules verdict — classification
never raises.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.classifier import extraction
from app.classifier.llm.base import ClassifyInput, LLMClient, LLMError
from app.classifier.llm.rules_client import RulesOnlyClient
from app.classifier.rules import get_rules_engine
from app.classifier.scoring import blend_confidence, compute_score
from app.core.logging import get_logger
from app.models.enums import IntentLabel

logger = get_logger(__name__)


class ClassificationResult(BaseModel):
    intent: IntentLabel
    confidence: int  # 0-100
    score: int  # 0-100 weighted lead score
    reasons: list[str]
    extracted: dict  # {product, price, currency, date, location}
    model: str  # "rules" | "claude:<model>" | "openai:<model>"
    rule_signals: dict


def classify_post(
    text: str,
    campaign_product: str | None = None,
    campaign_location: str | None = None,
    posted_at: datetime | None = None,
    llm_client: LLMClient | None = None,
    language: str = "en",
) -> ClassificationResult:
    engine = get_rules_engine(language)
    llm_client = llm_client or RulesOnlyClient(language)

    # --- Stage 1: rules ---
    signals = engine.analyze(text)
    rules_label, rules_conf, rules_reasons = engine.preliminary_label(signals)

    # --- Stage 2: LLM (graceful fallback to rules) ---
    inp = ClassifyInput(text=text, product=campaign_product, location=campaign_location)
    llm_ran = not isinstance(llm_client, RulesOnlyClient)
    model_name = getattr(llm_client, "model_id", llm_client.name)
    try:
        llm_result = llm_client.classify(inp, signals)
    except LLMError as exc:
        logger.warning("LLM classification failed (%s); using rules-only verdict", exc)
        llm_result = RulesOnlyClient(language).classify(inp, signals)
        llm_ran = False
        model_name = "rules"

    intent = llm_result.intent if llm_ran else rules_label

    # --- Stage 3: extraction (regex-first, LLM fills the gaps) ---
    price, currency = extraction.extract_price(text)
    extracted = {
        "product": extraction.extract_product(text, campaign_product) or llm_result.product,
        "price": price if price is not None else llm_result.price,
        "currency": currency or llm_result.currency,
        "date": extraction.extract_date(text) or llm_result.date,
        "location": extraction.extract_location(text, engine.locations, campaign_location) or llm_result.location,
    }

    product_matched = extraction.product_matches(text, campaign_product)
    location_matched = bool(
        campaign_location and extracted["location"] and campaign_location.lower() in str(extracted["location"]).lower()
    )

    score, score_reasons = compute_score(intent, signals, extracted, product_matched, location_matched, posted_at)
    confidence = blend_confidence(rules_conf, llm_result.confidence, llm_ran)

    # Merge and dedupe reasons, preserving order
    seen: set[str] = set()
    reasons = [r for r in (*rules_reasons, *llm_result.reasons, *score_reasons) if not (r in seen or seen.add(r))]

    return ClassificationResult(
        intent=intent,
        confidence=confidence,
        score=score,
        reasons=reasons[:10],
        extracted=extracted,
        model=model_name,
        rule_signals=signals.to_dict(),
    )
