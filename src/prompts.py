# src/prompts.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You create neutral, conceptual knowledge-check questions from a transcript.
Return ONLY a single JSON object that matches the schema given in the user message.
Do not include any commentary, Markdown, code fences, or explanations outside JSON.

Authoring rules:

1) Intro ("intro")
   - One concise, neutral sentence previewing the video’s topic.
   - Base ONLY on the transcript (no external context).
   - Avoid promotional language and dashes.

2) Key Quote ("key_quote")
   - Select ONE representative quote from the transcript.
   - Keep the wording EXACTLY as spoken (verbatim).

3) Multiple-Choice ("mc_questions")
   - Create exactly {n_mcq} conceptual questions.
   - Each MCQ has a stem and exactly 4 choices labeled A–D.
   - Exactly ONE choice has "correct": true; the other three are false.
   - Provide short, explanatory "feedback" for the correct answer.
   - Quality bar for stems:
       • 12–30 words.
       • Combine at least TWO related ideas from the transcript.
       • Prefer conceptual understanding to simple recall or numeric trivia.
       • Do NOT copy a single sentence and ask for a missing token.
   - Quality bar for distractors:
       • Plausible but wrong, and conceptually distinct from each other.
       • No “All of the above”, “None of the above”, or near-duplicates.
   - If you cannot find enough plausible distractors from the transcript,
     synthesize them so there are EXACTLY 4 choices.

4) True/False ("tf_questions")
   - Create exactly {n_tf} conceptual items.
   - Each has a clear statement, a boolean "answer", and short explanatory "feedback".
   - Statements should require reasoning, not recall of a single token or raw numbers.

General formatting:
- Use standard ASCII quotes in JSON strings.
- Return ONLY JSON that conforms to the schema in the user message.
- No trailing commentary, no Markdown.

Self-check BEFORE replying:
- You have exactly {n_mcq} MCQs and exactly {n_tf} T/F items.
- Every MCQ "choices" array has exactly 4 objects, labels are "A","B","C","D".
- Exactly one choice per MCQ has "correct": true (others false).
- All strings are valid JSON strings (ASCII quotes) and no extra fields are present.
If any check fails, fix your JSON and only then output it.
"""

USER_PROMPT = """\
Write {n_mcq} multiple-choice questions and {n_tf} true/false questions from this transcript.

Transcript:
{transcript}

Output JSON object with this exact shape:
{{
  "intro": string,
  "key_quote": string,
  "mc_questions": [
    {{
      "question": string,
      "choices": [
        {{"label": "A", "text": string, "correct": boolean}},
        {{"label": "B", "text": string, "correct": boolean}},
        {{"label": "C", "text": string, "correct": boolean}},
        {{"label": "D", "text": string, "correct": boolean}}
      ],
      "feedback": string
    }}
  ],
  "tf_questions": [
    {{"statement": string, "answer": boolean, "feedback": string}}
  ]
}}

Constraints (must all be satisfied):
- Exactly {n_mcq} MCQs and {n_tf} T/F items.
- Exactly 4 choices per MCQ, labeled A–D.
- Exactly ONE choice per MCQ has "correct": true (others false).
- No “All of the above” or “None of the above”.
- Keep feedback short and explanatory.
- Return ONLY the JSON object (no extra text, no Markdown).
"""


def build_prompt() -> ChatPromptTemplate:
    # default template_format is f-string; we intentionally keep {n_mcq}/{n_tf}/{transcript}
    # and escaped JSON braces {{ }} above.
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ]
    )
