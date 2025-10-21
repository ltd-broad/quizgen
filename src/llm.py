# src/llm.py
from __future__ import annotations

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from .prompts import build_prompt
from .schemas import Quiz

PROMPT = build_prompt()

def _make_llm(api_key: Optional[str]) -> ChatOpenAI:
    key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    return ChatOpenAI(
        model=os.getenv("QUIZGEN_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=key,
        timeout=90,
        max_retries=0,
    )

def get_quiz(transcript: str, n_mcq: int, n_tf: int, api_key: Optional[str] = None) -> Quiz:
    """
    Prompt (with counts) -> structured LLM -> Quiz (single invoke).
    """
    llm = _make_llm(api_key)
    structured_llm = llm.with_structured_output(Quiz)
    chain = PROMPT | structured_llm
    return chain.invoke({"transcript": transcript, "n_mcq": n_mcq, "n_tf": n_tf})