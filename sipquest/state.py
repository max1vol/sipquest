from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "./data")).expanduser().resolve()


def ensure_data_dir() -> Path:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def inventory_path() -> Path:
    return ensure_data_dir() / "inventory.json"


def dispense_events_path() -> Path:
    return ensure_data_dir() / "dispense_events.json"


def camera_events_path() -> Path:
    return ensure_data_dir() / "camera_events.json"


def last_camera_frame_path() -> Path:
    return ensure_data_dir() / "last_camera_frame.jpg"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_event_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{stamp}_{uuid4().hex[:8]}"


def read_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def append_json_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    events = read_json_array(path)
    events.append(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
    return event
