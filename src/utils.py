# src/utils.py
from __future__ import annotations
from typing import Any, Dict, List
import re

# Normalize curly quotes/dashes to ASCII to reduce quoting issues in HTML/JS
_ASCII = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "’": "'",
        "‘": "'",
        "—": "-",
        "–": "-",
    }
)


def normalize_text(s: str | None) -> str:
    s = (s or "").strip().translate(_ASCII)
    s = re.sub(r"\s+", " ", s)
    return s


_LABELS = ["A", "B", "C", "D"]


def _ensure_one_correct(choices: List[Dict[str, Any]]) -> None:
    # Keep only the first True; make sure there's at least one
    found = False
    for c in choices:
        if c.get("correct") and not found:
            found = True
        else:
            c["correct"] = False
    if not found and choices:
        choices[0]["correct"] = True


def _dedupe_choices(choices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for c in choices:
        text = normalize_text(c.get("text", ""))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {"label": None, "text": text, "correct": bool(c.get("correct", False))}
        )
    return out


def fix_mcq_choices(mcq: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize question
    mcq["question"] = normalize_text(mcq.get("question", ""))

    # Start with whatever the LLM returned
    choices = _dedupe_choices(list(mcq.get("choices") or []))

    # Trim or pad to exactly 4
    choices = choices[:4]
    while len(choices) < 4:
        choices.append(
            {
                "label": None,
                "text": f"None of the above ({len(choices)+1})",
                "correct": False,
            }
        )

    # Ensure exactly one correct
    _ensure_one_correct(choices)

    # Assign labels A–D
    for i, c in enumerate(choices):
        c["label"] = _LABELS[i]

    mcq["choices"] = choices
    # Normalize feedback if present
    mcq["feedback"] = normalize_text(mcq.get("feedback", ""))
    return mcq


def repair_quiz_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    data["intro"] = normalize_text(data.get("intro", ""))
    data["key_quote"] = normalize_text(data.get("key_quote", ""))

    mcqs = []
    for q in data.get("mc_questions", []) or []:
        mcqs.append(fix_mcq_choices(dict(q)))
    data["mc_questions"] = mcqs

    tfs = []
    for t in data.get("tf_questions", []) or []:
        tfs.append(
            {
                "statement": normalize_text(t.get("statement")),
                "answer": bool(t.get("answer", False)),
                "feedback": normalize_text(t.get("feedback")),
            }
        )
    data["tf_questions"] = tfs
    return data
