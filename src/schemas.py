from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class Choice(BaseModel):
    label: Literal["A", "B", "C", "D"]
    text: str
    correct: bool


class MCQuestion(BaseModel):
    question: str
    choices: List[Choice] = Field(min_length=4, max_length=4)
    feedback: Optional[str] = ""

    @model_validator(mode="after")
    def _one_correct(self):
        if sum(1 for c in self.choices if c.correct) != 1:
            raise ValueError("Exactly one choice must be correct.")
        return self


class TFQuestion(BaseModel):
    statement: str
    answer: bool
    feedback: Optional[str] = ""


class Quiz(BaseModel):
    intro: str
    # Optional full transcript text to show in an accordion
    transcript: Optional[str] = ""
    # Zero to five short, verbatim quotes to highlight from the transcript
    key_quotes: List[str] = Field(default_factory=list, max_length=5)
    mc_questions: List[MCQuestion] = Field(default_factory=list)
    tf_questions: List[TFQuestion] = Field(default_factory=list)
