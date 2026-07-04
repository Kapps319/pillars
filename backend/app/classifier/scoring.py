"""Stage 3 (part 2) — weighted lead scoring. All weights live in weights.yml."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import yaml

from app.classifier.rules import RuleSignals
from app.core.config import CONFIG_DIR
from app.models.enums import IntentLabel


@lru_cache
def load_weights() -> dict:
    with open(CONFIG_DIR / "weights.yml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def compute_score(
    intent: IntentLabel,
    signals: RuleSignals,
    extracted: dict,
    product_matched: bool,
    location_matched: bool,
    posted_at: datetime | None = None,
) -> tuple[int, list[str]]:
    """Return (score 0-100, reason tags explaining each contribution)."""
    cfg = load_weights()
    weights = cfg["weights"]
    score = float(cfg["base"].get(intent.value, 0))
    reasons: list[str] = []

    strong = signals.buy_matches if intent == IntentLabel.BUY else signals.sell_matches
    if intent in (IntentLabel.BUY, IntentLabel.SELL) and strong:
        score += weights["strong_keyword"]
        reasons.append(f"strong intent keywords ({len(strong)})")
    if product_matched:
        score += weights["product_match"]
        reasons.append("matches campaign product")
    if location_matched:
        score += weights["location_match"]
        reasons.append("matches campaign location")
    if extracted.get("date"):
        score += weights["date_match"]
        reasons.append(f"date mentioned: {extracted['date']}")
    if extracted.get("price") is not None:
        score += weights["price_mention"]
        reasons.append("price/budget stated")
    if signals.urgency_matches:
        score += weights["urgency"]
        reasons.append("urgency signals")
    if signals.contact_matches:
        score += weights["contactability"]
        reasons.append("contactable (DM/handle/phone)")
    if signals.spam_matches:
        score += weights["spam_penalty"]
        reasons.append("spam markers present (penalty)")

    if posted_at is not None:
        now = datetime.now(timezone.utc)
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        age_days = (now - posted_at).days
        if age_days <= cfg["recency_recent_days"]:
            score += weights["recency_recent"]
            reasons.append("posted recently")
        elif age_days >= cfg["recency_stale_days"]:
            score += weights["recency_stale"]
            reasons.append("stale post (penalty)")

    return max(0, min(100, round(score))), reasons


def blend_confidence(rules_confidence: int, llm_confidence: int | None, llm_ran: bool) -> int:
    """Combine rule signals + LLM into the final confidence."""
    if not llm_ran or llm_confidence is None:
        return rules_confidence
    w = float(load_weights()["llm_confidence_weight"])
    return max(0, min(100, round(rules_confidence * (1 - w) + llm_confidence * w)))
