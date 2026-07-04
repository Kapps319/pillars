"""Golden classifier tests — these encode the product's core promise and must
always pass. They run with the keyless RulesOnlyClient (the default backend).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.classifier.pipeline import classify_post
from app.models.enums import IntentLabel

RECENT = datetime.now(timezone.utc) - timedelta(days=1)


def test_golden_buy_high_score():
    result = classify_post(
        "Need 2 Abu Dhabi GP tickets, ready to buy today, DM me",
        campaign_product="Abu Dhabi GP tickets",
        campaign_location="Abu Dhabi",
        posted_at=RECENT,
    )
    assert result.intent == IntentLabel.BUY
    assert result.score >= 70, f"expected high score, got {result.score} ({result.reasons})"
    assert result.confidence >= 60
    assert result.reasons  # every lead must explain itself


def test_golden_mention_low_score():
    result = classify_post(
        "F1 tickets are crazy expensive",
        campaign_product="F1 tickets",
        posted_at=RECENT,
    )
    assert result.intent == IntentLabel.MENTION
    assert result.score <= 40, f"expected low score, got {result.score} ({result.reasons})"


def test_golden_sell_high_score():
    result = classify_post(
        "Selling 3 CAT1 World Cup tickets, asking $450 each, DM me. Can transfer today.",
        campaign_product="World Cup tickets",
        posted_at=RECENT,
    )
    assert result.intent == IntentLabel.SELL
    assert result.score >= 70, f"expected high score, got {result.score} ({result.reasons})"


def test_golden_spam_low_score():
    result = classify_post(
        "GIVEAWAY!! Follow and RT to win F1 tickets! Use code SPEED20, 100% legit, click here bit.ly/free",
        campaign_product="F1 tickets",
        posted_at=RECENT,
    )
    assert result.intent == IntentLabel.SPAM
    assert result.score <= 25, f"expected very low score, got {result.score} ({result.reasons})"


def test_extraction_price_location_date():
    result = classify_post(
        "Need 2 Abu Dhabi GP tickets, ready to buy today, DM me. Budget of $900.",
        campaign_product="Abu Dhabi GP tickets",
        campaign_location="Abu Dhabi",
        posted_at=RECENT,
    )
    extracted = result.extracted
    assert extracted["price"] == 900.0
    assert extracted["currency"] == "USD"
    assert extracted["location"] == "Abu Dhabi"
    assert extracted["date"] == "today"
    assert extracted["product"] == "Abu Dhabi GP tickets"


def test_anyone_selling_is_buy_not_sell():
    """'anyone selling' contains 'selling' but signals BUY intent."""
    result = classify_post("Is anyone selling 2 Coldplay tickets for Wembley?", campaign_product="Coldplay tickets")
    assert result.intent == IntentLabel.BUY


def test_classification_never_crashes_on_junk():
    for text in ["", "🤷", "a" * 5000, "1234567890 !!!"]:
        result = classify_post(text, campaign_product="tickets")
        assert result.intent in IntentLabel
        assert 0 <= result.score <= 100
        assert 0 <= result.confidence <= 100
