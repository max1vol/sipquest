from __future__ import annotations

from typing import Any

from .models import CameraInspection, DispenseResult, DrinkRequest, DrinkSlot, PickupConfirmation, SelectionResult


def generate_reveal(
    slot: DrinkSlot,
    request: DrinkRequest,
    camera_result: CameraInspection,
    dispense_result: DispenseResult,
    pickup_result: PickupConfirmation | None = None,
    selection_result: SelectionResult | None = None,
) -> dict[str, Any]:
    caffeine_free_delivered = not slot.caffeine
    safety_override = bool(selection_result and selection_result.safety_override_applied)
    if request.avoid_caffeine:
        safety_explanation = "Caffeine-free mode was applied, so the clear bottle was selected."
    else:
        safety_explanation = "No caffeine-free constraint was requested; selection stayed within visible in-stock bottles."

    return {
        "flavorName": slot.display_name,
        "slotId": slot.slot_id,
        "rarity": slot.rarity,
        "badge": slot.badge,
        "artTitle": slot.art_title,
        "setProgress": f"{slot.set_name} {slot.set_slot}/{slot.set_total}",
        "story": slot.story,
        "safety": {
            "caffeineFreeRequested": request.avoid_caffeine,
            "caffeineFreeDelivered": caffeine_free_delivered,
            "safetyOverrideApplied": safety_override,
            "explanation": safety_explanation,
        },
        "responsibleRandomness": {
            "noCashValue": True,
            "noResalePromise": True,
            "noPaidReroll": True,
            "explanation": "Rarity affects only story, art, badge, and collection progress.",
        },
        "physicalProof": {
            "cameraSource": camera_result.source,
            "visibleBeforeDispense": camera_result.visible_bottles,
            "dispenseEventId": dispense_result.event_id,
            "pickupConfirmed": pickup_result.confirmed if pickup_result else False,
            "pickupSource": pickup_result.source if pickup_result else None,
            "cameraWarning": camera_result.warning,
            "pickupWarning": pickup_result.warning if pickup_result else None,
        },
    }


def _format_seen_bottles(values: list[str]) -> str:
    if not values:
        return "camera inconclusive"
    names = {"blue": "blue bottle", "clear": "clear bottle"}
    return ", ".join(names.get(value, value) for value in values)


def format_reveal_response(
    reveal: dict[str, Any],
    selection: SelectionResult,
    dispense: DispenseResult,
    pickup: PickupConfirmation,
) -> str:
    rarity = str(reveal["rarity"]).title()
    proof = reveal["physicalProof"]
    pickup_text = "confirmed" if pickup.confirmed else "not confirmed"
    if pickup.source == "bench":
        pickup_text = "bench confirmed"

    lines = [
        f"Done — SipQuest dispensed slot {reveal['slotId']}: {reveal['flavorName']}.",
        "",
        "Why this bottle:",
        selection.reason,
        "",
        "FlavourDex reveal:",
        f"{reveal['flavorName']} — {rarity}",
        f"Badge unlocked: {reveal['badge']}",
        f"Art: {reveal['artTitle']}",
        f"Set progress: {reveal['setProgress']}",
        "",
        "Physical proof:",
        f"Camera saw: {_format_seen_bottles(proof['visibleBeforeDispense'])}.",
        f"Dispense event: {proof['dispenseEventId'] or dispense.mode}.",
        f"Pickup confirmation: {pickup_text}.",
        "",
        "Responsible randomness:",
        "This is a playful mystery reveal, not gambling. No cash value, no resale promise, no paid reroll.",
        "Rarity only changes story, art, badge, and collection progress.",
    ]

    warnings = [proof.get("cameraWarning"), proof.get("pickupWarning"), dispense.error]
    visible_warnings = [warning for warning in warnings if warning]
    if visible_warnings:
        lines.extend(["", "Hardware note:", " ".join(visible_warnings)])

    return "\n".join(lines)
