from __future__ import annotations

import json

from sipquest.box_controller import dispense_bottle
from sipquest.camera_vision import inspect_box
from sipquest.intent import parse_drink_request
from sipquest.inventory import choose_bottle, load_inventory
from sipquest.models import CameraInspection
from sipquest.reveal import generate_reveal


def test_parse_caffeine_free_request():
    request = parse_drink_request("I want a mystery drink, caffeine-free.")

    assert request.requested_vibe == "wildcard"
    assert request.avoid_caffeine is True
    assert request.explicit_bottle is None


def test_parse_wildcard_request():
    request = parse_drink_request("Give me a wildcard mystery drink.")

    assert request.requested_vibe == "wildcard"
    assert request.avoid_caffeine is False


def test_caffeine_free_request_chooses_crystal_chill():
    inventory = load_inventory("data/inventory.json")
    request = parse_drink_request("I want a mystery drink, caffeine-free.")
    camera = CameraInspection(visible_bottles=["blue", "clear"], confidence=1.0, source="bench")

    selection = choose_bottle(request, inventory, camera)

    assert selection.slot is not None
    assert selection.slot.display_name == "Crystal Chill"
    assert selection.safety_override_applied is True


def test_explicit_blue_and_caffeine_free_falls_back_to_crystal_chill():
    inventory = load_inventory("data/inventory.json")
    request = parse_drink_request("I want the blue one but caffeine-free.")
    camera = CameraInspection(visible_bottles=["blue", "clear"], confidence=1.0, source="bench")

    selection = choose_bottle(request, inventory, camera)

    assert selection.slot is not None
    assert selection.slot.display_name == "Crystal Chill"
    assert "blue bottle is marked as caffeinated" in selection.reason


def test_wildcard_without_restrictions_chooses_blue_nova():
    inventory = load_inventory("data/inventory.json")
    request = parse_drink_request("Give me a wildcard mystery drink.")
    camera = CameraInspection(visible_bottles=["blue", "clear"], confidence=1.0, source="bench")

    selection = choose_bottle(request, inventory, camera)

    assert selection.slot is not None
    assert selection.slot.display_name == "Blue Nova"


def test_no_safe_option_returns_failure():
    inventory = load_inventory("data/inventory.json")
    modified = [
        slot if slot.vision_hint != "clear" else type(slot)(**{**slot.to_dict(), "in_stock": False})
        for slot in inventory
    ]
    request = parse_drink_request("Do not give me caffeine.")
    camera = CameraInspection(visible_bottles=["blue", "clear"], confidence=1.0, source="bench")

    selection = choose_bottle(request, modified, camera)

    assert selection.slot is None
    assert selection.refusal_reason


def test_bench_dispense_writes_event(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BENCH_BOX", "true")
    inventory = load_inventory("data/inventory.json")
    slot = next(item for item in inventory if item.slot_id == "B1")

    result = dispense_bottle("B1", slot)

    assert result.success is True
    events = json.loads((tmp_path / "dispense_events.json").read_text(encoding="utf-8"))
    assert events[-1]["slot_id"] == "B1"
    assert events[-1]["display_name"] == "Crystal Chill"


def test_reveal_includes_responsible_randomness(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAMERA_MODE", "bench")
    inventory = load_inventory("data/inventory.json")
    request = parse_drink_request("I want a mystery drink, caffeine-free.")
    camera = inspect_box()
    selection = choose_bottle(request, inventory, camera)
    assert selection.slot is not None
    dispense = type("Dispense", (), {"event_id": "dispense_test"})()
    pickup = type("Pickup", (), {"confirmed": True, "source": "bench", "warning": None})()

    reveal = generate_reveal(selection.slot, request, camera, dispense, pickup, selection)

    assert reveal["responsibleRandomness"]["noCashValue"] is True
    assert reveal["responsibleRandomness"]["noResalePromise"] is True
    assert reveal["responsibleRandomness"]["noPaidReroll"] is True
