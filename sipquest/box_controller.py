from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .camera_vision import inspect_box
from .state import append_json_event, bool_env, dispense_events_path, new_event_id, utc_now_iso
from .inventory import load_inventory
from .models import DispenseResult, DrinkSlot, PickupConfirmation

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _slot_name(slot_id: str) -> str:
    try:
        slot = next((item for item in load_inventory() if item.slot_id == slot_id), None)
    except Exception:
        slot = None
    return slot.display_name if slot else "unknown bottle"


def _bench_dispense(slot_id: str, slot: DrinkSlot | None = None) -> DispenseResult:
    event_id = new_event_id("dispense")
    display_name = slot.display_name if slot else _slot_name(slot_id)
    event = {
        "event_id": event_id,
        "timestamp": utc_now_iso(),
        "mode": "bench",
        "slot_id": slot_id,
        "display_name": display_name,
        "success": True,
    }
    append_json_event(dispense_events_path(), event)
    print(f"SIPQUEST BOX: DISPENSED SLOT {slot_id} — {display_name}", flush=True)
    return DispenseResult(
        success=True,
        mode="bench",
        event_id=event_id,
        slot_id=slot_id,
        message=f"Bench dispense recorded for slot {slot_id}: {display_name}.",
        raw=event,
    )


def _http_dispense(slot_id: str) -> DispenseResult:
    base_url = os.getenv("BOX_CONTROLLER_URL", "").strip().rstrip("/")
    if not base_url:
        return DispenseResult(
            success=False,
            mode="http",
            slot_id=slot_id,
            message="BOX_CONTROLLER_URL is not set.",
            error="BOX_CONTROLLER_URL is not set. Use BENCH_BOX=true for bench mode.",
        )

    payload = json.dumps({"slot_id": slot_id}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/dispense",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.getenv("BOX_CONTROLLER_TIMEOUT_SECONDS", "8"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return DispenseResult(
            success=False,
            mode="http",
            slot_id=slot_id,
            message="Hardware controller request failed.",
            error=f"Could not reach box controller: {exc.__class__.__name__}. Use BENCH_BOX=true to keep the flow running.",
        )

    return DispenseResult(
        success=bool(data.get("success", True)),
        mode="http",
        event_id=data.get("event_id"),
        slot_id=slot_id,
        message=str(data.get("message", f"Controller dispensed slot {slot_id}.")),
        raw=data,
    )


def _serial_dispense(slot_id: str) -> DispenseResult:
    port = os.getenv("SERIAL_PORT", "").strip()
    try:
        import serial

        with serial.Serial(port, baudrate=int(os.getenv("SERIAL_BAUD", "9600")), timeout=2) as handle:
            handle.write(f"{slot_id}\n".encode("utf-8"))
    except Exception as exc:
        return DispenseResult(
            success=False,
            mode="serial",
            slot_id=slot_id,
            message="Serial dispense failed.",
            error=f"Could not write to SERIAL_PORT: {exc.__class__.__name__}. Use BENCH_BOX=true to keep the flow running.",
        )

    event_id = new_event_id("serial")
    return DispenseResult(
        success=True,
        mode="serial",
        event_id=event_id,
        slot_id=slot_id,
        message=f"Serial command sent for slot {slot_id}.",
    )


def _voice_ai_hat_dispense(slot_id: str, slot: DrinkSlot | None = None) -> DispenseResult:
    try:
        from sipquest_voice_box.hardware import HatHardware

        hardware = HatHardware(
            button_gpio=int(os.getenv("BUTTON_GPIO", "23")),
            led_gpio=int(os.getenv("LED_GPIO", "25")),
            pull_up=bool_env("BUTTON_PULL_UP", True),
        )
        hardware.blink(on_seconds=0.08, off_seconds=0.08)
        time.sleep(float(os.getenv("DISPENSE_SIGNAL_SECONDS", "1.2")))
        hardware.confirm_clear()
        hardware.off()
    except Exception as exc:
        return DispenseResult(
            success=False,
            mode="hat",
            slot_id=slot_id,
            message="Voice box hardware signal failed.",
            error=f"Could not signal the box hardware: {exc.__class__.__name__}. Use BENCH_BOX=true for bench testing.",
        )

    event_id = new_event_id("hat_dispense")
    display_name = slot.display_name if slot else _slot_name(slot_id)
    event = {
        "event_id": event_id,
        "timestamp": utc_now_iso(),
        "mode": "hat",
        "slot_id": slot_id,
        "display_name": display_name,
        "success": True,
    }
    append_json_event(dispense_events_path(), event)
    print(f"SIPQUEST BOX: HARDWARE SIGNALED SLOT {slot_id} — {display_name}", flush=True)
    return DispenseResult(
        success=True,
        mode="hat",
        event_id=event_id,
        slot_id=slot_id,
        message=f"Box hardware signaled for slot {slot_id}: {display_name}.",
        raw=event,
    )


def dispense_bottle(slot_id: str, slot: DrinkSlot | None = None) -> DispenseResult:
    if bool_env("BENCH_BOX", True):
        return _bench_dispense(slot_id, slot)
    backend = os.getenv("BOX_HARDWARE_BACKEND", "").strip().lower()
    if backend == "hat":
        return _voice_ai_hat_dispense(slot_id, slot)
    if os.getenv("BOX_CONTROLLER_URL", "").strip():
        return _http_dispense(slot_id)
    if os.getenv("SERIAL_PORT", "").strip():
        return _serial_dispense(slot_id)
    return DispenseResult(
        success=False,
        mode="none",
        slot_id=slot_id,
        message="No box controller mode is configured.",
        error="Set BENCH_BOX=true, BOX_CONTROLLER_URL, or SERIAL_PORT.",
    )


def confirm_pickup(slot_id: str) -> PickupConfirmation:
    if bool_env("BENCH_PICKUP", True):
        return PickupConfirmation(confirmed=True, source="bench")

    if not bool_env("CAMERA_CONFIRM_PICKUP", False):
        return PickupConfirmation(
            confirmed=False,
            source="not-configured",
            warning="Pickup confirmation is disabled; dispense command was still issued.",
        )

    try:
        slot = next(item for item in load_inventory() if item.slot_id == slot_id)
        inspection = inspect_box()
    except Exception:
        return PickupConfirmation(
            confirmed=False,
            source="camera",
            warning="Camera confirmation inconclusive; dispense command was still issued.",
        )

    if slot.vision_hint not in inspection.visible_bottles:
        return PickupConfirmation(confirmed=True, source=inspection.source)

    return PickupConfirmation(
        confirmed=False,
        source=inspection.source,
        warning="Camera confirmation inconclusive; dispense command was still issued.",
    )
