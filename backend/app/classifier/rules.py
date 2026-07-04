"""Stage 1 — rules filter.

Detects strong intent phrases and pre-filters obvious noise using the pattern
lists in app/config/keywords.yml. Everything language-specific lives in that
YAML file; this module only compiles and applies it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import CONFIG_DIR
from app.models.enums import IntentLabel

_SPAN = tuple[int, int]


@dataclass
class RuleSignals:
    """Everything stage 1 learned about a post."""

    buy_matches: list[str] = field(default_factory=list)
    sell_matches: list[str] = field(default_factory=list)
    spam_matches: list[str] = field(default_factory=list)
    mention_matches: list[str] = field(default_factory=list)
    urgency_matches: list[str] = field(default_factory=list)
    contact_matches: list[str] = field(default_factory=list)
    price_question_matches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "buy": self.buy_matches,
            "sell": self.sell_matches,
            "spam": self.spam_matches,
            "mention": self.mention_matches,
            "urgency": self.urgency_matches,
            "contact": self.contact_matches,
            "price_question": self.price_question_matches,
        }


class RulesEngine:
    def __init__(self, language: str = "en", config_path: Path | None = None):
        path = config_path or CONFIG_DIR / ("keywords.yml" if language == "en" else f"keywords.{language}.yml")
        with open(path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        self.locations: list[str] = cfg.get("locations", [])
        self._compiled: dict[str, list[re.Pattern]] = {
            key: [re.compile(p, re.IGNORECASE) for p in cfg.get(key, [])]
            for key in (
                "buy_patterns",
                "sell_patterns",
                "spam_patterns",
                "mention_patterns",
                "urgency_patterns",
                "contact_patterns",
                "price_question_patterns",
            )
        }

    @staticmethod
    def _find(patterns: list[re.Pattern], text: str) -> list[tuple[str, _SPAN]]:
        hits: list[tuple[str, _SPAN]] = []
        for pattern in patterns:
            for m in pattern.finditer(text):
                hits.append((m.group(0), m.span()))
        return hits

    def analyze(self, text: str) -> RuleSignals:
        buy = self._find(self._compiled["buy_patterns"], text)
        buy_spans = [span for _, span in buy]

        # A sell match nested inside a buy phrase is not a sell signal:
        # "anyone selling" matches the buy list, so its inner "selling" must
        # not count as SELL intent.
        def outside_buy(span: _SPAN) -> bool:
            return not any(span[0] >= b[0] and span[1] <= b[1] for b in buy_spans)

        sell = [(t, s) for t, s in self._find(self._compiled["sell_patterns"], text) if outside_buy(s)]

        return RuleSignals(
            buy_matches=[t for t, _ in buy],
            sell_matches=[t for t, _ in sell],
            spam_matches=[t for t, _ in self._find(self._compiled["spam_patterns"], text)],
            mention_matches=[t for t, _ in self._find(self._compiled["mention_patterns"], text)],
            urgency_matches=[t for t, _ in self._find(self._compiled["urgency_patterns"], text)],
            contact_matches=[t for t, _ in self._find(self._compiled["contact_patterns"], text)],
            price_question_matches=[t for t, _ in self._find(self._compiled["price_question_patterns"], text)],
        )

    def preliminary_label(self, signals: RuleSignals) -> tuple[IntentLabel, int, list[str]]:
        """Rules-only verdict: (label, confidence 0-100, human-readable reasons)."""
        n_buy, n_sell, n_spam = len(signals.buy_matches), len(signals.sell_matches), len(signals.spam_matches)

        # Spam pre-filter: multiple spam markers, or spam markers with no
        # transactional signal at all, is treated as spam.
        if n_spam >= 2 or (n_spam == 1 and n_buy == 0 and n_sell == 0):
            reasons = [f"spam marker: '{m}'" for m in signals.spam_matches[:3]]
            return IntentLabel.SPAM, min(60 + 10 * n_spam, 95), reasons

        if n_buy > 0 or n_sell > 0:
            if n_buy >= n_sell:
                label, matches = IntentLabel.BUY, signals.buy_matches
            else:
                label, matches = IntentLabel.SELL, signals.sell_matches
            confidence = min(55 + 12 * min(len(matches), 3), 92)
            reasons = [f"strong {label.value.lower()} phrase: '{m}'" for m in matches[:3]]
            if signals.contact_matches:
                reasons.append(f"contact info present: '{signals.contact_matches[0]}'")
            if signals.urgency_matches:
                reasons.append(f"urgency: '{signals.urgency_matches[0]}'")
            return label, confidence, reasons

        if signals.mention_matches:
            return (
                IntentLabel.MENTION,
                70,
                [f"casual mention/noise marker: '{signals.mention_matches[0]}'"],
            )
        return IntentLabel.MENTION, 45, ["no transactional intent phrases found"]


@lru_cache
def get_rules_engine(language: str = "en") -> RulesEngine:
    return RulesEngine(language=language)
