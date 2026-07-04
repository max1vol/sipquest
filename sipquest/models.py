from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DrinkRequest:
    requested_vibe: str
    avoid_caffeine: bool
    explicit_bottle: str | None
    wants_inventory: bool
    raw_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DrinkSlot:
    slot_id: str
    physical_name: str
    display_name: str
    vibes: list[str]
    caffeine: bool
    rarity: str
    badge: str
    art_title: str
    set_name: str
    set_slot: int
    set_total: int
    story: str
    in_stock: bool
    vision_hint: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrinkSlot":
        return cls(
            slot_id=str(data["slot_id"]),
            physical_name=str(data["physical_name"]),
            display_name=str(data["display_name"]),
            vibes=[str(vibe) for vibe in data.get("vibes", [])],
            caffeine=bool(data["caffeine"]),
            rarity=str(data["rarity"]),
            badge=str(data["badge"]),
            art_title=str(data["art_title"]),
            set_name=str(data["set_name"]),
            set_slot=int(data["set_slot"]),
            set_total=int(data["set_total"]),
            story=str(data["story"]),
            in_stock=bool(data["in_stock"]),
            vision_hint=str(data["vision_hint"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def caffeine_label(self) -> str:
        return "caffeinated" if self.caffeine else "caffeine-free"


@dataclass(frozen=True)
class CameraInspection:
    visible_bottles: list[str]
    confidence: float
    source: str
    selected_frame_path: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SelectionResult:
    slot: DrinkSlot | None
    reason: str
    safety_override_applied: bool = False
    fallback_applied: bool = False
    refusal_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["slot"] = self.slot.to_dict() if self.slot else None
        return result


@dataclass(frozen=True)
class DispenseResult:
    success: bool
    mode: str
    message: str
    event_id: str | None = None
    slot_id: str | None = None
    error: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PickupConfirmation:
    confirmed: bool
    source: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
