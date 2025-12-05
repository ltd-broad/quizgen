# src/schemas.py
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Choice(BaseModel):
    label: Literal["A", "B", "C", "D"]
    text: str
    correct: bool


class MCQuestion(BaseModel):
    question: str
    # Exactly 4 choices; enforced by min_length/max_length
    choices: List[Choice] = Field(min_length=4, max_length=4)
    feedback: Optional[str] = ""

    @model_validator(mode="after")
    def _one_correct(self) -> "MCQuestion":
        """Enforce that exactly one choice is marked correct."""
        if sum(1 for c in self.choices if c.correct) != 1:
            raise ValueError("Exactly one choice must be correct.")
        return self


class TFQuestion(BaseModel):
    statement: str
    answer: bool
    feedback: Optional[str] = ""


class Quiz(BaseModel):
    intro: str

    # Up to FIVE short, representative quotes to highlight from the transcript.
    #
    # IMPORTANT:
    # - We intentionally enforce ONLY a maximum of 5 (max_length=5).
    # - There is NO min_length, so a filtered quiz with 0 quotes
    #   (when the instructor selects “None”) will still validate.
    # - At generation time, repair_quiz_dict() normalizes the raw model
    #   output to exactly 5 quotes for the draft UI.
    key_quotes: List[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "Zero to five short, representative quotes from the transcript. "
            "Generation-time repair logic pads/truncates to 5 for the draft, "
            "but the final filtered quiz may contain fewer (including 0) "
            "if the instructor chooses not to embed a quote."
        ),
    )

    mc_questions: List[MCQuestion] = Field(default_factory=list)
    tf_questions: List[TFQuestion] = Field(default_factory=list)
