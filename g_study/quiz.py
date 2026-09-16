from __future__ import annotations

import random
from typing import Any

from .exam_questions import filter_exam_questions
from .terms import all_terms, filter_terms

QUIZ_PRESETS = [
    {"n": 3, "label": "3問", "hint": "約1分"},
    {"n": 5, "label": "5問", "hint": "約2分"},
    {"n": 10, "label": "10問", "hint": "約4分"},
    {"n": 15, "label": "15問", "hint": "約6分"},
]


def _choices_for(correct: dict, pool: list[dict], n: int = 4) -> list[str]:
    others = [t for t in pool if t["term"] != correct["term"]]
    if len(others) < n - 1:
        others = [t for t in all_terms() if t["term"] != correct["term"]]
    sampled = random.sample(others, k=min(n - 1, len(others)))
    options = [correct["term"]] + [t["term"] for t in sampled]
    random.shuffle(options)
    return options


def make_question(pool: list[dict] | None = None) -> dict[str, Any]:
    source = pool if pool else all_terms()
    if len(source) < 2:
        source = all_terms()
    item = random.choice(source)
    mode = random.choice(["def_to_term", "point_to_term"])
    if mode == "point_to_term":
        stem = f"次の試験ポイントが指す用語はどれか。\n\n{item['exam_point']}"
    else:
        stem = f"次の説明に最も当てはまる用語はどれか。\n\n{item['definition']}"
    options = _choices_for(item, source)
    return {
        "term": item["term"],
        "definition": item["definition"],
        "exam_point": item["exam_point"],
        "field": item["field"],
        "chapter": item["chapter"],
        "section": item["section"],
        "pdf": item.get("pdf", ""),
        "stem": stem,
        "options": options,
        "answer": item["term"],
        "kind": "term",
    }


def _prepare_exam(q: dict) -> dict:
    options = list(q["options"])
    random.shuffle(options)
    out = dict(q)
    out["options"] = options
    return out


def make_quiz(
    n: int = 5,
    chapter: str | None = None,
    field: str | None = None,
    terms: list[str] | None = None,
) -> list[dict]:
    explicit = terms is not None
    if explicit:
        wanted = set(terms)
        pool = [t for t in all_terms() if t["term"] in wanted]
        if not pool:
            return []
    else:
        pool = filter_terms(field=field, chapter=chapter)
        if len(pool) < 2:
            pool = all_terms()
    exam = filter_exam_questions(
        chapter=None if explicit else chapter,
        field=None if explicit else field,
        terms=list(wanted) if explicit else None,
    )
    count = min(max(1, n), max(len(pool), len(exam), 1))
    used_stems: set[str] = set()
    used_terms: set[str] = set()
    questions = []
    random.shuffle(exam)
    for q in exam:
        if len(questions) >= count:
            break
        if q["stem"] in used_stems:
            continue
        used_stems.add(q["stem"])
        used_terms.add(q["term"])
        questions.append(_prepare_exam(q))
    guard = 0
    while len(questions) < count and guard < count * 12:
        q = make_question(pool)
        guard += 1
        if q["term"] in used_terms or q["stem"] in used_stems:
            continue
        used_terms.add(q["term"])
        used_stems.add(q["stem"])
        questions.append(q)
    random.shuffle(questions)
    return questions
