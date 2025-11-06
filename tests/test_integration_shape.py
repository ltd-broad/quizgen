# tests/test_integration_shape.py
import os
import pytest
from src import llm
from src.schemas import Quiz

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Set OPENAI_API_KEY to run integration tests against the real API.",
)
def test_live_openai_returns_four_choices():
    """
    Hits the real API with a tiny transcript and asserts
    the returned shape always has exactly 4 choices per MCQ.
    """
    transcript = "This short video introduces R-squared in linear regression."
    quiz = llm.get_quiz(transcript, n_mcq=2, n_tf=1, api_key=None, max_attempts=5)

    assert isinstance(quiz, Quiz)
    assert len(quiz.mc_questions) == 2
    for q in quiz.mc_questions:
        assert len(q.choices) == 4
        assert sum(1 for c in q.choices if c.correct) == 1
