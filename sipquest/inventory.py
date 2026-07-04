from __future__ import annotations

import json
from pathlib import Path

from .state import inventory_path
from .models import CameraInspection, DrinkRequest, DrinkSlot, SelectionResult


QUEST_DIRECTIONS = {"chill", "energy", "wildcard", "blue", "clear"}


def load_inventory(path: str | Path | None = None) -> list[DrinkSlot]:
    source = Path(path) if path else inventory_path()
    data = json.loads(source.read_text(encoding="utf-8"))
    return [DrinkSlot.from_dict(item) for item in data]


def inventory_as_dicts(inventory: list[DrinkSlot]) -> list[dict[str, object]]:
    return [slot.to_dict() for slot in inventory]


def format_inventory(inventory: list[DrinkSlot]) -> str:
    lines = ["SipQuest box inventory:"]
    for slot in inventory:
        stock = "in stock" if slot.in_stock else "out of stock"
        caffeine = "contains caffeine" if slot.caffeine else "caffeine-free"
        lines.append(
            f"- {slot.slot_id}: {slot.display_name} ({slot.physical_name}), "
            f"{caffeine}, vibes: {', '.join(slot.vibes)}, {stock}"
        )
    return "\n".join(lines)


def is_ambiguous_request(request: DrinkRequest) -> bool:
    if request.wants_inventory:
        return False
    if request.explicit_bottle:
        return False
    if request.requested_vibe in QUEST_DIRECTIONS:
        return False
    return not request.avoid_caffeine


def _visible_filtered(slots: list[DrinkSlot], camera_result: CameraInspection) -> list[DrinkSlot]:
    visible = set(camera_result.visible_bottles or [])
    if not visible:
        return slots
    visible_slots = [slot for slot in slots if slot.vision_hint in visible]
    return visible_slots or slots


def _find_by_hint(slots: list[DrinkSlot], hint: str) -> DrinkSlot | None:
    return next((slot for slot in slots if slot.vision_hint == hint), None)


def _find_by_vibe(slots: list[DrinkSlot], vibe: str) -> DrinkSlot | None:
    return next((slot for slot in slots if vibe in slot.vibes), None)


def _safe_slots(slots: list[DrinkSlot], request: DrinkRequest) -> list[DrinkSlot]:
    if request.avoid_caffeine:
        return [slot for slot in slots if not slot.caffeine]
    return slots


def _no_safe(reason: str) -> SelectionResult:
    return SelectionResult(slot=None, reason=reason, refusal_reason=reason)


def choose_bottle(
    request: DrinkRequest,
    inventory: list[DrinkSlot],
    camera_result: CameraInspection,
) -> SelectionResult:
    in_stock = [slot for slot in inventory if slot.in_stock]
    if not in_stock:
        return _no_safe("No bottles are marked in stock, so SipQuest did not dispense.")

    available = _visible_filtered(in_stock, camera_result)
    blue = _find_by_hint(available, "blue")
    clear = _find_by_hint(available, "clear")
    safe_available = _safe_slots(available, request)

    if request.explicit_bottle == "clear":
        if clear:
            return SelectionResult(
                slot=clear,
                reason="I selected Crystal Chill because you explicitly asked for the clear bottle.",
                safety_override_applied=request.avoid_caffeine,
            )
        return _no_safe("The clear bottle is not available or not visible, so SipQuest did not dispense.")

    if request.explicit_bottle == "blue":
        if request.avoid_caffeine:
            if clear:
                return SelectionResult(
                    slot=clear,
                    reason=(
                        "I selected Crystal Chill because you asked for caffeine-free, "
                        "and the blue bottle is marked as caffeinated."
                    ),
                    safety_override_applied=True,
                    fallback_applied=True,
                )
            return _no_safe("You asked for caffeine-free, but no caffeine-free bottle is available.")
        if blue:
            return SelectionResult(
                slot=blue,
                reason="I selected Blue Nova because you explicitly asked for the blue bottle.",
            )
        return _no_safe("The blue bottle is not available or not visible, so SipQuest did not dispense.")

    if request.avoid_caffeine:
        clear_safe = _find_by_hint(safe_available, "clear")
        if clear_safe:
            return SelectionResult(
                slot=clear_safe,
                reason=(
                    "I selected Crystal Chill because you asked for caffeine-free, "
                    "and the blue bottle is marked as caffeinated."
                ),
                safety_override_applied=True,
                fallback_applied=request.requested_vibe in {"energy", "blue", "wildcard"},
            )
        return _no_safe("You asked for caffeine-free, but no caffeine-free bottle is available.")

    if request.requested_vibe in {"chill", "clear"}:
        if clear:
            return SelectionResult(
                slot=clear,
                reason="I selected Crystal Chill because you asked for a chill or clear drink.",
            )
        return _no_safe("No chill or clear bottle is available.")

    if request.requested_vibe in {"energy", "blue"}:
        if blue:
            return SelectionResult(
                slot=blue,
                reason="I selected Blue Nova because you asked for energy or blue.",
            )
        if clear:
            return SelectionResult(
                slot=clear,
                reason="Blue Nova was not available, so I selected the visible clear fallback.",
                fallback_applied=True,
            )
        return _no_safe("No energy or blue bottle is available.")

    if request.requested_vibe == "wildcard":
        if blue:
            return SelectionResult(
                slot=blue,
                reason="I selected Blue Nova for a wildcard mystery because no safety constraint blocked it.",
            )
        if clear:
            return SelectionResult(
                slot=clear,
                reason="Blue Nova was not available, so I selected Crystal Chill as the safe wildcard fallback.",
                fallback_applied=True,
            )
        return _no_safe("No wildcard bottle is available.")

    caffeine_free = _find_by_vibe(safe_available, "caffeine-free")
    if caffeine_free:
        return SelectionResult(
            slot=caffeine_free,
            reason="I selected Crystal Chill because your only clear constraint was to avoid caffeine.",
            safety_override_applied=True,
        )

    return _no_safe("The request needs a quest direction before SipQuest can safely choose a bottle.")
