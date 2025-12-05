from __future__ import annotations

import json
from typing import Optional

from pydantic import ValidationError
from openai import BadRequestError, OpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import Quiz
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .utils import repair_quiz_dict

# You can change this if you want to try another model, e.g. "gpt-4.1-mini".
MODEL_NAME = "o3-mini"


def _build_messages(transcript: str, n_mcq: int, n_tf: int) -> list[dict]:
    """Format the prompt into OpenAI chat-completion messages.

    We keep using ChatPromptTemplate for convenience, then convert each
    LangChain message into a simple {"role": ..., "content": ...} dict that
    the OpenAI client expects.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ]
    )
    lc_messages = prompt.format_messages(
        transcript=transcript,
        n_mcq=n_mcq,
        n_tf=n_tf,
    )

    messages: list[dict] = []
    for m in lc_messages:
        msg_type = getattr(m, "type", "user")  # e.g. "system", "human", "ai"

        # Map LangChain's "human" -> OpenAI's "user"
        if msg_type == "human":
            role = "user"
        elif msg_type in ("system", "user", "assistant"):
            role = msg_type
        else:
            # Fallback – treat anything unknown as "user"
            role = "user"

        content = m.content

        # LangChain messages can sometimes hold content as a list of parts.
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                else:
                    text_parts.append(str(part))
            content = "\n".join(text_parts)

        messages.append({"role": role, "content": content})

    return messages


def _one_generation_attempt(
    *,
    transcript: str,
    n_mcq: int,
    n_tf: int,
    api_key: Optional[str],
) -> Quiz:
    """Perform ONE full attempt to obtain a valid Quiz.

    For non-reasoning models (model names *not* starting with ``"o3-"``),
    we send ``temperature=0.0`` to make the behaviour more deterministic.

    For reasoning models like ``"o3-mini"``, the OpenAI API does **not**
    support a ``temperature`` parameter at all. By using the low-level
    OpenAI client directly and only adding ``temperature`` for non-o3
    models, we avoid the "Unsupported parameter: 'temperature'" error.
    """
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    messages = _build_messages(transcript=transcript, n_mcq=n_mcq, n_tf=n_tf)

    # Base request payload
    request_kwargs: dict = {
        "model": MODEL_NAME,
        "messages": messages,
        # Ask the model to return a pure JSON object in its message content
        "response_format": {"type": "json_object"},
    }

    # Only non-o3 models get an explicit temperature parameter.
    if not MODEL_NAME.startswith("o3-"):
        request_kwargs["temperature"] = 0.0

    # Single model call for this attempt
    resp = client.chat.completions.create(**request_kwargs)
    raw = resp.choices[0].message.content

    # First parse attempt
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
        repair_kwargs = dict(request_kwargs)
        repair_kwargs["messages"] = repair_messages

        resp = client.chat.completions.create(**repair_kwargs)
        raw = resp.choices[0].message.content
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
    """Deterministic, robust generation with bounded retries.

    - For non-o3 models we set ``temperature=0.0`` when calling the API.
    - For reasoning models like ``o3-mini`` we omit ``temperature`` entirely
      so the request is accepted by the API.
    - We retry when the output fails validation (e.g., MCQ not exactly 4
      choices). On the first valid result we return immediately.
    - After ``max_attempts`` failures, we raise the last error seen.
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

    # Fallback (should not happen in practice)
    raise RuntimeError(f"Failed to produce a valid quiz after {max_attempts} attempts.")
