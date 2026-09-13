from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import PROGRESS_PATH, DATA_DIR


def _empty() -> dict:
    return {
        "known": [],
        "unknown": [],
        "quiz": {"answered": 0, "correct": 0, "history": []},
        "updated": "",
    }


def load_progress() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_PATH.exists():
        return _empty()
    try:
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty()
    base = _empty()
    base.update(data)
    base.setdefault("known", [])
    base.setdefault("unknown", [])
    base.setdefault("quiz", {"answered": 0, "correct": 0, "history": []})
    return base


def save_progress(data: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    PROGRESS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return PROGRESS_PATH


def mark_card(data: dict, term: str, known: bool) -> dict:
    known_set = set(data.get("known", []))
    unknown_set = set(data.get("unknown", []))
    if known:
        known_set.add(term)
        unknown_set.discard(term)
    else:
        unknown_set.add(term)
        known_set.discard(term)
    data["known"] = sorted(known_set)
    data["unknown"] = sorted(unknown_set)
    return data


def record_quiz(data: dict, correct: bool, term: str) -> dict:
    quiz = data.setdefault("quiz", {"answered": 0, "correct": 0, "history": []})
    quiz["answered"] = int(quiz.get("answered", 0)) + 1
    if correct:
        quiz["correct"] = int(quiz.get("correct", 0)) + 1
    history = quiz.setdefault("history", [])
    history.append(
        {
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "term": term,
            "correct": bool(correct),
        }
    )
    quiz["history"] = history[-200:]
    return data
