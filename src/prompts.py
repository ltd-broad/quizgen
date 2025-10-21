# src/prompts.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_RULES = """You create neutral practice questions from a transcript.
Return ONLY valid JSON that matches the provided schema. Do not include prose outside JSON.

Authoring rules:
1) Video Introduction (intro)
   - One concise, neutral sentence previewing the video.
   - Base ONLY on the transcript; do not add external context.
   - Avoid promotional language.
   - Do not use dashes.

2) Key Quote (key_quote)
   - Select one representative quote from the transcript.
   - Enclose it in quotation marks.
   - Keep the wording exactly as spoken.

3) Multiple-Choice Questions (mc_questions)
   - Create exactly five conceptual questions testing ideas from the transcript (not trivia or single-line numerics).
   - Each question must have EXACTLY 4 choices labeled A, B, C, D.
   - Randomize which choice is correct (not always the same position).
   - Include a short 'feedback' explanation for the correct answer.

4) True/False Questions (tf_questions)
   - Create exactly five conceptual true/false items.
   - Each item has 'statement', 'answer' (True or False), and a short 'feedback' explanation.

General constraints:
- Prefer general concepts over specific numbers, single-line jargon, or one-off details.
- Keep language clear and concise for learners.
"""

HUMAN_TEMPLATE = """Transcript:
{transcript}

Produce the JSON only, conforming EXACTLY to the schema in the format instructions below.

{format_instructions}
"""

def build_prompt() -> ChatPromptTemplate:
    # NOTE: we keep {format_instructions} as a placeholder.
    # We'll inject the actual (brace-heavy) text via .partial(...) in llm.py
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_RULES),
            ("human", HUMAN_TEMPLATE),
        ]
    )