# src/llm.py
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableSequence

from .schemas import Quiz
from .prompts import build_prompt

# Single-call client (no retries, no max_tokens cap)
LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)

PARSER = PydanticOutputParser(pydantic_object=Quiz)

# Build prompt, then freeze the brace-heavy format instructions via partial()
PROMPT = build_prompt().partial(format_instructions=PARSER.get_format_instructions())

# Compose prompt -> model -> parser
CHAIN: RunnableSequence = PROMPT | LLM | PARSER

def get_quiz(transcript: str) -> Quiz:
    # Exactly one API call; if parsing fails, it raises
    return CHAIN.invoke({"transcript": transcript})