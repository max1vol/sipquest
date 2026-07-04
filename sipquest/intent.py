from __future__ import annotations

import re

from .models import DrinkRequest


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def parse_drink_request(text: str) -> DrinkRequest:
    raw_text = text or ""
    normalized = raw_text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)

    wants_inventory = _contains_any(
        normalized,
        [
            "what drinks",
            "what bottles",
            "what is in the box",
            "what's in the box",
            "what do you have",
            "available",
            "inventory",
            "in stock",
            "show me the box",
        ],
    )

    avoid_caffeine = _contains_any(
        normalized,
        [
            "caffeine-free",
            "caffeine free",
            "no caffeine",
            "avoid caffeine",
            "without caffeine",
            "do not give me caffeine",
            "don't give me caffeine",
            "decaf",
            "not energy",
            "safe drink",
        ],
    )

    explicit_bottle: str | None = None
    if _has_word(normalized, "clear") or "transparent" in normalized:
        explicit_bottle = "clear"
    elif _has_word(normalized, "blue"):
        explicit_bottle = "blue"

    requested_vibe = "unknown"
    if explicit_bottle:
        requested_vibe = explicit_bottle
    elif _contains_any(normalized, ["wildcard", "random", "mystery", "surprise"]):
        requested_vibe = "wildcard"
    elif _contains_any(normalized, ["chill", "calm", "refreshing"]):
        requested_vibe = "chill"
    elif _contains_any(normalized, ["energy", "boost"]) and "not energy" not in normalized:
        requested_vibe = "energy"

    return DrinkRequest(
        requested_vibe=requested_vibe,
        avoid_caffeine=avoid_caffeine,
        explicit_bottle=explicit_bottle,
        wants_inventory=wants_inventory,
        raw_text=raw_text,
    )
