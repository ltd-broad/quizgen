# src/prompts.py
# Purpose: Build the chat prompt used to turn a transcript into a Quiz JSON.
# Notes:
# - No {format_instructions} placeholder is required because we use
#   llm.with_structured_output(Quiz), which injects the necessary guidance.

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_RULES = """
You create neutral practice questions from a transcript.
Return ONLY valid JSON that matches the provided schema. Do not include prose outside JSON.

Authoring rules:
1) Intro (intro)
   - One concise, neutral sentence previewing the video.
   - Base ONLY on the transcript; add no external context.
   - Avoid promotional language and dashes.
2) Key Quote (key_quote)
   - Select one representative quote from the transcript.
   - Keep the wording exactly as spoken.
3) Multiple-Choice Questions (mc_questions)
   - Create exactly five conceptual questions that test ideas (not trivia or single-line recall).
   - Each question has four choices labeled A–D.
   - Randomize which choice is correct.
   - Include a short feedback line for the correct answer.
4) True/False Questions (tf_questions)
   - Create exactly five conceptual items.
   - Include a short feedback line for the answer.
""".strip()

HUMAN_TEMPLATE = """
Use the transcript below to produce the JSON described above.

Transcript:
{transcript}
""".strip()

def build_prompt() -> ChatPromptTemplate:
    """Return the chat prompt template used by the chain."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_RULES),
            ("human", HUMAN_TEMPLATE),
        ]
    )