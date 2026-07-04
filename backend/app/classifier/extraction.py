"""Stage 3 (part 1) — deterministic field extraction: price, date, location, product."""

from __future__ import annotations

import re

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}
_CURRENCY_WORDS = {
    "usd": "USD", "dollars": "USD", "dollar": "USD",
    "eur": "EUR", "euros": "EUR", "euro": "EUR",
    "gbp": "GBP", "pounds": "GBP", "pound": "GBP", "quid": "GBP",
    "aed": "AED", "dirhams": "AED",
    "sar": "SAR", "cad": "CAD", "aud": "AUD",
}

# "$450", "AED 2,400,000", "€1.5k"
_PRICE_SYMBOL_RE = re.compile(r"([$€£]|\b(?:AED|USD|EUR|GBP|SAR|CAD|AUD)\b)\s?(\d[\d,]*(?:\.\d+)?)(k)?", re.IGNORECASE)
# "450 dollars", "1900 aed"
_PRICE_WORD_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)(k)?\s?(" + "|".join(_CURRENCY_WORDS) + r")\b", re.IGNORECASE
)

_MONTHS = (
    "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    "aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_DATE_RES = [
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.IGNORECASE),  # "July 19"
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\b", re.IGNORECASE),      # "19 July"
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),                                                # ISO
    re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),                                     # 19/7/2026
    re.compile(r"\b(?:today|tonight|tomorrow|this week(?:end)?)\b", re.IGNORECASE),      # relative
]

_STOPWORDS = {"the", "a", "an", "of", "for", "in", "to", "and", "or"}


def extract_price(text: str) -> tuple[float | None, str | None]:
    m = _PRICE_SYMBOL_RE.search(text)
    if m:
        symbol, number, kilo = m.group(1), m.group(2), m.group(3)
        currency = _CURRENCY_SYMBOLS.get(symbol, symbol.upper())
        value = float(number.replace(",", "")) * (1000 if kilo else 1)
        return value, currency
    m = _PRICE_WORD_RE.search(text)
    if m:
        number, kilo, word = m.group(1), m.group(2), m.group(3)
        value = float(number.replace(",", "")) * (1000 if kilo else 1)
        return value, _CURRENCY_WORDS[word.lower()]
    return None, None


def extract_date(text: str) -> str | None:
    for pattern in _DATE_RES:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


def extract_location(text: str, gazetteer: list[str], campaign_location: str | None = None) -> str | None:
    lowered = text.lower()
    # A campaign's own location wins if it appears in the post
    if campaign_location and campaign_location.lower() in lowered:
        return campaign_location
    for place in gazetteer:
        if re.search(rf"\b{re.escape(place.lower())}\b", lowered):
            return place
    return None


def product_matches(text: str, campaign_product: str | None) -> bool:
    """True when the meaningful tokens of the campaign product appear in the post."""
    if not campaign_product:
        return False
    lowered = text.lower()
    tokens = [t for t in re.split(r"\W+", campaign_product.lower()) if t and t not in _STOPWORDS]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}", lowered))
    return hits >= max(1, len(tokens) // 2 + (0 if len(tokens) > 1 else 0))


def extract_product(text: str, campaign_product: str | None) -> str | None:
    return campaign_product if product_matches(text, campaign_product) else None
