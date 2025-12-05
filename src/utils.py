# src/utils.py
from __future__ import annotations

import json
from typing import Any, Dict, List


def _ensure_list(value: Any) -> List[Any]:
    """Helper: turn a value into a list (or empty list)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def repair_quiz_dict(raw: Any) -> Dict[str, Any]:
    """Best-effort cleanup of the raw model output before Pydantic validation.

    Goals:
    - Ensure we always have a dict with the keys intro, key_quotes,
      mc_questions, tf_questions.
    - Force key_quotes to be a list of EXACTLY 5 strings so that the
      Quiz schema (which expects 5 quotes) does not fail purely because
      of quote count.
    - Keep MC/TF question lists well-formed enough for Pydantic +
      retry logic to do the final enforcement.
    """

    # If the model returned a JSON string inside another layer, try to
    # parse it once.
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            # If we can't parse, fall back to an empty structure and let
            # Pydantic / retries handle the failure.
            raw = {}

    if not isinstance(raw, dict):
        # Fallback to an empty dict; this will likely fail validation and
        # trigger a retry in get_quiz.
        raw = {}

    data: Dict[str, Any] = dict(raw)

    # -------- Intro --------
    intro = data.get("intro")
    if not isinstance(intro, str):
        intro = ""  # Safe default
    data["intro"] = intro

    # -------- Key Quotes: ensure EXACTLY 5 strings --------
    raw_quotes = _ensure_list(data.get("key_quotes"))
    cleaned_quotes: List[str] = []

    for q in raw_quotes:
        if isinstance(q, str):
            s = q.strip()
            if s:
                cleaned_quotes.append(s)

    # If we have >= 5, truncate to 5.
    if len(cleaned_quotes) >= 5:
        cleaned_quotes = cleaned_quotes[:5]
    elif len(cleaned_quotes) == 0:
        # No usable quotes at all: fall back to intro (or a generic placeholder)
        base = intro.strip() or "Key idea from the transcript."
        cleaned_quotes = [base] * 5
    else:
        # 1–4 quotes: pad by repeating the last one until we reach 5.
        last = cleaned_quotes[-1]
        while len(cleaned_quotes) < 5:
            cleaned_quotes.append(last)

    data["key_quotes"] = cleaned_quotes

    # -------- Multiple-choice questions --------
    mc_raw = data.get("mc_questions", [])
    if not isinstance(mc_raw, list):
        mc_raw = _ensure_list(mc_raw)
    data["mc_questions"] = mc_raw

    # -------- True/False questions --------
    tf_raw = data.get("tf_questions", [])
    if not isinstance(tf_raw, list):
        tf_raw = _ensure_list(tf_raw)
    data["tf_questions"] = tf_raw

    return data
