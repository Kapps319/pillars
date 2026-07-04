from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.classifier.rules import RuleSignals, get_rules_engine
from app.classifier.scoring import blend_confidence, compute_score
from app.models.enums import IntentLabel


def _signals(**kwargs) -> RuleSignals:
    return RuleSignals(**kwargs)


def test_spam_penalty_applies():
    clean, _ = compute_score(IntentLabel.BUY, _signals(buy_matches=["wtb"]), {}, False, False)
    spammy, _ = compute_score(
        IntentLabel.BUY, _signals(buy_matches=["wtb"], spam_matches=["promo code"]), {}, False, False
    )
    assert spammy < clean


def test_recency_bonus_and_stale_penalty():
    now = datetime.now(timezone.utc)
    recent, _ = compute_score(IntentLabel.BUY, _signals(buy_matches=["wtb"]), {}, False, False, now)
    stale, _ = compute_score(
        IntentLabel.BUY, _signals(buy_matches=["wtb"]), {}, False, False, now - timedelta(days=120)
    )
    assert recent > stale


def test_full_signal_stack_reaches_100():
    signals = _signals(buy_matches=["wtb", "ready to buy"], urgency_matches=["today"], contact_matches=["dm me"])
    extracted = {"price": 900.0, "date": "today"}
    score, reasons = compute_score(
        IntentLabel.BUY, signals, extracted, True, True, datetime.now(timezone.utc)
    )
    assert score == 100
    assert len(reasons) >= 5


def test_score_clamped_to_bounds():
    score, _ = compute_score(IntentLabel.SPAM, _signals(spam_matches=["casino", "promo code"]), {}, False, False)
    assert score == 0


def test_blend_confidence():
    assert blend_confidence(50, None, llm_ran=False) == 50
    blended = blend_confidence(40, 90, llm_ran=True)
    assert 40 < blended <= 90


def test_rules_engine_spam_prefilter():
    engine = get_rules_engine()
    signals = engine.analyze("Use code WIN50, guaranteed profit! Click here bit.ly/x")
    label, confidence, reasons = engine.preliminary_label(signals)
    assert label == IntentLabel.SPAM
    assert reasons
