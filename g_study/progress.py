from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, PROGRESS_PATH
from .runtime import disk_writable
from .terms import all_terms, chapters, find_term


def _empty() -> dict:
    return {
        "known": [],
        "unknown": [],
        "quiz": {"answered": 0, "correct": 0, "history": []},
        "sessions": [],
        "card_history": [],
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
    return _normalize(data)


def _normalize(data: dict) -> dict:
    base = _empty()
    base.update(data or {})
    quiz = base.setdefault("quiz", {"answered": 0, "correct": 0, "history": []})
    quiz.setdefault("answered", 0)
    quiz.setdefault("correct", 0)
    quiz.setdefault("history", [])
    base.setdefault("known", [])
    base.setdefault("unknown", [])
    base.setdefault("sessions", [])
    base.setdefault("card_history", [])
    return base


def load_progress_bytes(raw: bytes) -> dict:
    return _normalize(json.loads(raw.decode("utf-8")))


def progress_bytes(data: dict) -> bytes:
    payload = _normalize(data)
    payload["updated"] = datetime.now().isoformat(timespec="seconds")
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def save_progress(data: dict) -> Path | None:
    if not disk_writable(DATA_DIR):
        return None
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    PROGRESS_PATH.write_text(json.dumps(_normalize(data), ensure_ascii=False, indent=2), encoding="utf-8")
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


def record_card(data: dict, term: str, known: bool, chapter: str = "", field: str = "") -> dict:
    data = mark_card(data, term, known)
    hist = data.setdefault("card_history", [])
    hist.append(
        {
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "term": term,
            "known": bool(known),
            "chapter": chapter,
            "field": field,
        }
    )
    data["card_history"] = hist[-300:]
    return data


def record_quiz(
    data: dict,
    correct: bool,
    term: str,
    chapter: str = "",
    field: str = "",
    section: str = "",
) -> dict:
    quiz = data.setdefault("quiz", {"answered": 0, "correct": 0, "history": []})
    quiz["answered"] = int(quiz.get("answered", 0)) + 1
    if correct:
        quiz["correct"] = int(quiz.get("correct", 0)) + 1
    history = quiz.setdefault("history", [])
    history.append(
        {
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "kind": "quiz",
            "term": term,
            "correct": bool(correct),
            "chapter": chapter or _chapter_of(term),
            "field": field,
            "section": section,
        }
    )
    quiz["history"] = history[-400:]
    return data


def record_session(
    data: dict,
    chapter: str | None,
    n: int,
    answered: int,
    correct: int,
) -> dict:
    sessions = data.setdefault("sessions", [])
    sessions.append(
        {
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "chapter": chapter or "全範囲",
            "n": int(n),
            "answered": int(answered),
            "correct": int(correct),
        }
    )
    data["sessions"] = sessions[-100:]
    return data


def _chapter_of(term: str) -> str:
    found = find_term(term)
    return found["chapter"] if found else ""


def chapter_stats(data: dict) -> list[dict]:
    hist = data.get("quiz", {}).get("history", [])
    known = set(data.get("known", []))
    unknown = set(data.get("unknown", []))
    by_ch: dict[str, dict] = defaultdict(lambda: {"answered": 0, "correct": 0})
    for row in hist:
        ch = row.get("chapter") or _chapter_of(row.get("term", "")) or "未分類"
        by_ch[ch]["answered"] += 1
        if row.get("correct"):
            by_ch[ch]["correct"] += 1

    rows = []
    for chapter in chapters():
        total = len([t for t in all_terms() if t["chapter"] == chapter])
        names = {t["term"] for t in all_terms() if t["chapter"] == chapter}
        stats = by_ch.get(chapter, {"answered": 0, "correct": 0})
        answered = stats["answered"]
        correct = stats["correct"]
        rows.append(
            {
                "章": chapter,
                "用語数": total,
                "カード既知": len(names & known),
                "要復習": len(names & unknown),
                "クイズ解答": answered,
                "クイズ正解": correct,
                "正答率": round(100 * correct / answered) if answered else None,
            }
        )
    extra = [ch for ch in by_ch if ch not in {r["章"] for r in rows}]
    for chapter in extra:
        stats = by_ch[chapter]
        answered = stats["answered"]
        rows.append(
            {
                "章": chapter,
                "用語数": 0,
                "カード既知": 0,
                "要復習": 0,
                "クイズ解答": answered,
                "クイズ正解": stats["correct"],
                "正答率": round(100 * stats["correct"] / answered) if answered else None,
            }
        )
    return rows


def daily_quiz_counts(data: dict) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in data.get("quiz", {}).get("history", []):
        day = str(row.get("at", ""))[:10]
        if day:
            counts[day] += 1
    return dict(sorted(counts.items()))


def weak_terms_from_history(data: dict, limit: int = 20) -> list[dict]:
    misses: Counter[str] = Counter()
    hits: Counter[str] = Counter()
    last_at: dict[str, str] = {}
    for row in data.get("quiz", {}).get("history", []):
        term = row.get("term") or ""
        if not term:
            continue
        last_at[term] = row.get("at", "")
        if row.get("correct"):
            hits[term] += 1
        else:
            misses[term] += 1
    ranked = []
    for term, n_miss in misses.most_common(limit):
        ranked.append(
            {
                "用語": term,
                "不正解": n_miss,
                "正解": hits.get(term, 0),
                "章": _chapter_of(term),
                "最終": last_at.get(term, ""),
            }
        )
    return ranked
