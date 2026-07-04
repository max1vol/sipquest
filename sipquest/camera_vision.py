from __future__ import annotations

import os
import sys

from .state import append_json_event, camera_events_path, last_camera_frame_path, new_event_id, utc_now_iso
from .models import CameraInspection


def _record_camera_event(result: CameraInspection) -> CameraInspection:
    append_json_event(
        camera_events_path(),
        {
            "event_id": new_event_id("cam"),
            "timestamp": utc_now_iso(),
            "result": result.to_dict(),
        },
    )
    return result


def _bench_inspection() -> CameraInspection:
    return CameraInspection(visible_bottles=["blue", "clear"], confidence=1.0, source="bench")


def _parse_visible(raw: str) -> list[str]:
    visible: list[str] = []
    normalized = raw.lower()
    if "blue" in normalized:
        visible.append("blue")
    if "clear" in normalized or "white" in normalized or "transparent" in normalized:
        visible.append("clear")
    return visible


def _manual_inspection() -> CameraInspection:
    file_path = os.getenv("CAMERA_MANUAL_FILE", "").strip()
    raw = os.getenv("CAMERA_MANUAL_VISIBLE", "").strip()
    if file_path and os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as handle:
            raw = handle.read().strip()
    elif not raw and sys.stdin.isatty():
        raw = input("SipQuest camera manual mode. Visible bottles (blue, clear, both, none): ").strip()

    visible = _parse_visible(raw)
    warning = None if visible else "Manual camera mode did not report a visible box bottle."
    return CameraInspection(visible_bottles=visible, confidence=0.95 if visible else 0.0, source="manual", warning=warning)


def _opencv_inspection() -> CameraInspection:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return CameraInspection(
            visible_bottles=[],
            confidence=0.0,
            source="opencv",
            warning=f"OpenCV camera inspection unavailable: {exc.__class__.__name__}. Falling back to inventory.",
        )

    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return CameraInspection(
            visible_bottles=[],
            confidence=0.0,
            source="opencv",
            warning="Webcam could not be opened. Falling back to inventory.",
        )

    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        return CameraInspection(
            visible_bottles=[],
            confidence=0.0,
            source="opencv",
            warning="Webcam frame capture failed. Falling back to inventory.",
        )

    frame_path = last_camera_frame_path()
    cv2.imwrite(str(frame_path), frame)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    total_pixels = frame.shape[0] * frame.shape[1]

    blue_lower = np.array([90, 60, 40])
    blue_upper = np.array([135, 255, 255])
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
    blue_ratio = float(cv2.countNonZero(blue_mask)) / float(total_pixels)

    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    clear_mask = cv2.inRange(saturation, 0, 55) & cv2.inRange(value, 150, 255)
    clear_ratio = float(cv2.countNonZero(clear_mask)) / float(total_pixels)

    visible: list[str] = []
    if blue_ratio > 0.005:
        visible.append("blue")
    if clear_ratio > 0.02:
        visible.append("clear")

    confidence = max(min((blue_ratio * 20.0) + (clear_ratio * 8.0), 1.0), 0.0)
    warning = None
    if not visible:
        warning = "Camera did not confidently detect either box bottle. Falling back to inventory."

    return CameraInspection(
        visible_bottles=visible,
        selected_frame_path=str(frame_path),
        confidence=round(confidence, 3),
        source="opencv",
        warning=warning,
    )


def inspect_box() -> CameraInspection:
    mode = os.getenv("CAMERA_MODE", "bench").strip().lower()
    if mode == "bench":
        return _record_camera_event(_bench_inspection())
    if mode == "manual":
        return _record_camera_event(_manual_inspection())
    if mode == "opencv":
        return _record_camera_event(_opencv_inspection())

    result = _bench_inspection()
    result = CameraInspection(
        visible_bottles=result.visible_bottles,
        confidence=result.confidence,
        source="bench",
        warning=f"Unknown CAMERA_MODE={mode!r}; used bench camera state.",
    )
    return _record_camera_event(result)
