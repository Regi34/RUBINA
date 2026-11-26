"""Manajemen state JSON kantor virtual agar frontend GitHub Pages selalu sinkron."""

import json
from datetime import datetime, timezone
from typing import Any

from agents.config import HISTORY_FILE, STATE_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {
            "updated_at": _now_iso(),
            "active_episode": None,
            "office_status": "idle",
            "agents": {},
            "stats": {"total_scripts": 0, "total_published": 0},
            "recent_videos": [],
        }
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _now_iso()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_agent_status(
    agent_key: str,
    status: str,
    message: str,
    office_status: str | None = None,
    active_episode: dict[str, Any] | None = None,
) -> None:
    state = load_state()
    if agent_key in state.get("agents", {}):
        state["agents"][agent_key]["status"] = status
        state["agents"][agent_key]["message"] = message
    if office_status is not None:
        state["office_status"] = office_status
    if active_episode is not None:
        state["active_episode"] = active_episode
    save_state(state)


def reset_agents_idle(office_status: str = "idle") -> None:
    default_msgs = {
        "scriptwriter": "Siap menulis cerita seru untuk anak-anak!",
        "safety_guard": "Memastikan semua naskah aman & edukatif.",
        "voice_actor": "Mikrofon siap untuk suara ceria!",
        "illustrator": "Palet warna cerah sudah siap.",
        "video_editor": "Timeline siap merakit video Shorts.",
        "publisher": "Menunggu video final untuk diupload.",
    }
    state = load_state()
    for key, info in state.get("agents", {}).items():
        info["status"] = "idle"
        if key in default_msgs:
            info["message"] = default_msgs[key]
    state["office_status"] = office_status
    save_state(state)


def record_published_video(video_entry: dict[str, Any]) -> None:
    state = load_state()
    stats = state.setdefault("stats", {"total_scripts": 0, "total_published": 0})
    stats["total_published"] = stats.get("total_published", 0) + 1
    recent = state.setdefault("recent_videos", [])
    recent.insert(0, video_entry)
    state["recent_videos"] = recent[:20]
    state["active_episode"] = None
    save_state(state)


def increment_script_count() -> None:
    state = load_state()
    stats = state.setdefault("stats", {"total_scripts": 0, "total_published": 0})
    stats["total_scripts"] = stats.get("total_scripts", 0) + 1
    save_state(state)


def load_history() -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return list(data.get("topics", []))


def append_history(topic: str) -> None:
    topics = load_history()
    if topic and topic not in topics:
        topics.append(topic)
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps({"topics": topics[-100:]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
