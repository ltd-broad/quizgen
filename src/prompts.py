# src/prompts.py
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
   - Create exactly {n_mcq} conceptual questions that test ideas (not trivia or single-line recall).
   - Each question has four choices labeled A–D.
   - Randomize which choice is correct.
   - Include a short feedback line for the correct answer.
   - Each MCQ stem should be 12–30 words and combine at least two related ideas from the transcript.
   - Avoid stems that quote a single sentence and ask for a missing noun.
   - Avoid questions whose only difficulty is recalling exact variable names (e.g., x1/x2) or raw numeric trivia; prefer conceptual understanding instead.
   - Make distractors plausible but wrong and conceptually distinct.
   - Do not use options like "All of the above" or "None of the above".
4) True/False Questions (tf_questions)
   - Create exactly {n_tf} conceptual items.
   - Include a short feedback line for the answer.
   - Write statements that require reasoning, not recall of a single token or variable name.
""".strip()

HUMAN_TEMPLATE = """
Use the transcript below to produce the JSON described above.

Transcript:
{transcript}
""".strip()

def build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_RULES),
        ("human", HUMAN_TEMPLATE),
    ])