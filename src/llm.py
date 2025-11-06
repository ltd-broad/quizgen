# src/llm.py
from __future__ import annotations
import json
from typing import Optional

from pydantic import ValidationError
from openai import BadRequestError  # <-- NEW: catch OpenAI schema errors
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import Quiz
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .utils import repair_quiz_dict


def get_quiz(
    transcript: str, n_mcq: int, n_tf: int, api_key: Optional[str] = None
) -> Quiz:
    """
    Deterministic, robust generation:
    1) Try strict structured output (Pydantic parsing).
    2) If it fails (incl. OpenAI schema rejection), fall back to JSON mode,
       repair, then validate with Pydantic.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ]
    )
    messages = prompt.format_messages(transcript=transcript, n_mcq=n_mcq, n_tf=n_tf)

    # Fast path: strict structured output directly to Quiz
    strict_llm = llm.with_structured_output(Quiz, strict=True)
    try:
        return strict_llm.invoke(messages)
    except (ValidationError, BadRequestError):
        # - ValidationError: model output didn't satisfy schema
        # - BadRequestError: OpenAI rejected the schema itself (e.g. missing additionalProperties:false)
        # Try once more with lower temperature for compliance; otherwise fall back.
        try:
            llm.temperature = 0.0
            strict_llm = llm.with_structured_output(Quiz, strict=True)
            return strict_llm.invoke(messages)
        except (ValidationError, BadRequestError):
            pass

    # Fallback: raw JSON, then repair, then validate
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
    return Quiz.model_validate(repaired)
