# src/llm.py
from __future__ import annotations
import json
from typing import Optional

from pydantic import ValidationError
from openai import BadRequestError  # OpenAI schema/response errors
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import Quiz
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .utils import repair_quiz_dict


def _one_generation_attempt(
    *,
    transcript: str,
    n_mcq: int,
    n_tf: int,
    api_key: Optional[str],
) -> Quiz:
    """
    Perform ONE full attempt to obtain a valid Quiz with temperature=0.0:
      1) strict structured output (Pydantic) once
      2) strict structured output again (in case of transient issues)
      3) JSON fallback -> repair -> Pydantic validate
    Raises ValidationError/BadRequestError/JSON errors if still invalid.
    """
    # Deterministic model configuration
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,  # fully deterministic for structured output
        api_key=api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ]
    )
    messages = prompt.format_messages(transcript=transcript, n_mcq=n_mcq, n_tf=n_tf)

    # 1) strict structured output (Pydantic) – first try
    try:
        strict_llm = llm.with_structured_output(Quiz, strict=True)
        return strict_llm.invoke(messages)
    except (ValidationError, BadRequestError):
        pass

    # 2) strict structured output – second try (same deterministic config)
    try:
        strict_llm = llm.with_structured_output(Quiz, strict=True)
        return strict_llm.invoke(messages)
    except (ValidationError, BadRequestError):
        pass

    # 3) JSON fallback -> repair -> validate
    json_llm = llm.bind(response_format={"type": "json_object"})
    raw = json_llm.invoke(messages).content  # string JSON
    try:
        data = json.loads(raw)
    except Exception:
        # One more nudge for valid JSON if needed
        repair_messages = messages + [
            {
                "role": "system",
                "content": "Return a single valid JSON object matching the Quiz schema.",
            }
        ]
        raw = json_llm.invoke(repair_messages).content
        data = json.loads(raw)

    repaired = repair_quiz_dict(data)
    return Quiz.model_validate(repaired)  # may raise ValidationError


def get_quiz(
    transcript: str,
    n_mcq: int,
    n_tf: int,
    api_key: Optional[str] = None,
    *,
    max_attempts: int = 5,
) -> Quiz:
    """
    Deterministic, robust generation with bounded retries.
    - Temperature is 0.0 everywhere (best for schema compliance).
    - We only retry when the output fails validation (e.g., MCQ not exactly 4 choices).
    - On first valid result, return immediately.
    - After `max_attempts` failures, raise the last error.

    Args:
        transcript: raw transcript text
        n_mcq: number of multiple-choice questions requested
        n_tf: number of true/false questions requested
        api_key: optional per-call API key override
        max_attempts: maximum full attempts (default 5)

    Returns:
        Quiz (validated Pydantic model)

    Raises:
        ValidationError (or BadRequestError/JSON errors) if all attempts fail.
    """
    last_err: Exception | None = None

    for _ in range(max_attempts):
        try:
            return _one_generation_attempt(
                transcript=transcript,
                n_mcq=n_mcq,
                n_tf=n_tf,
                api_key=api_key,
            )
        except (ValidationError, BadRequestError, json.JSONDecodeError) as e:
            last_err = e
            continue

    # Exhausted attempts without a valid quiz — raise the last error
    if last_err is not None:
        raise last_err
    # Fallback (should not happen)
    raise ValidationError(
        f"Failed to produce a valid quiz after {max_attempts} attempts."
    )
