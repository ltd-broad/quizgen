# src/schemas.py
from typing import List
from pydantic import BaseModel, Field, model_validator

class MCChoice(BaseModel):
    label: str = Field(..., description="A, B, C, or D")
    text: str = Field(..., min_length=1)
    correct: bool

class MCQuestion(BaseModel):
    question: str = Field(..., min_length=5)
    choices: List[MCChoice]
    feedback: str = Field(..., min_length=3)

    @model_validator(mode="after")
    def _check_choices(self):
        labels = [c.label for c in self.choices]
        if len(self.choices) != 4:
            raise ValueError("MCQuestion must have exactly 4 choices.")
        if sorted(labels) != ["A", "B", "C", "D"]:
            raise ValueError("Choice labels must be exactly A, B, C, D.")
        correct_count = sum(1 for c in self.choices if c.correct)
        if correct_count != 1:
            raise ValueError("Exactly one MC choice must be correct.")
        return self

class TFQuestion(BaseModel):
    statement: str = Field(..., min_length=5)
    answer: bool
    feedback: str = Field(..., min_length=3)

class Quiz(BaseModel):
    intro: str = Field(..., description="One concise, neutral sentence preview")
    key_quote: str = Field(..., description="Verbatim quote enclosed in quotation marks")
    mc_questions: List[MCQuestion]
    tf_questions: List[TFQuestion]

    @model_validator(mode="after")
    def _check_counts(self):
        # Allow variable counts selected in the UI (dropdowns). Keep sensible bounds
        # so accidental empty outputs are rejected.
        if not (1 <= len(self.mc_questions) <= 10):
            raise ValueError("Quiz must have between 1 and 10 multiple-choice questions.")
        if not (1 <= len(self.tf_questions) <= 10):
            raise ValueError("Quiz must have between 1 and 10 true/false questions.")
        return self