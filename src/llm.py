# src/llm.py
# Purpose: Create the LLM and the chain that returns a structured Quiz object.
# Contract: get_quiz(transcript: str, api_key: Optional[str]) -> Quiz
# - Exactly one model call (no retries, no background work).
# - If api_key is None, we fall back to the OPENAI_API_KEY env var.

from __future__ import annotations

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from .prompts import build_prompt
from .schemas import Quiz  # Pydantic model defining the expected JSON

# Build the prompt once
PROMPT = build_prompt()

def _make_llm(api_key: Optional[str]) -> ChatOpenAI:
    """Create a ChatOpenAI client with explicit key precedence."""
    key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    return ChatOpenAI(
        model=os.getenv("QUIZGEN_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=key,
        timeout=90,       # fail fast instead of hanging
        max_retries=0,    # guarantee exactly one network attempt
    )

def get_quiz(transcript: str, api_key: Optional[str] = None) -> Quiz:
    """
    Build the chain: Prompt -> LLM with structured output -> Quiz (Pydantic).
    Exactly one invoke; raises if the model output can't be parsed into Quiz.
    """
    llm = _make_llm(api_key)

    # Ask LangChain to enforce the Quiz schema.
    # In current LangChain, this returns a Runnable that already handles
    # schema instructions internally—no need to inject format_instructions.
    structured_llm = llm.with_structured_output(Quiz)

    # Compose: prompt | structured_llm
    chain = PROMPT | structured_llm

    # Single call; no retries (keeps costs predictable)
    return chain.invoke({"transcript": transcript})