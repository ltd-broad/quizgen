# src/prompts.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You create neutral, conceptual knowledge-check questions from a transcript
for graduate-level students in a higher-education (university) context.
Return ONLY a single JSON object that matches the schema given in the user message.
Do not include any commentary, Markdown, code fences, or explanations outside JSON.

Authoring rules:

1) Intro ("intro")
   - One concise, neutral sentence previewing the video’s topic.
   - Base ONLY on the transcript (no external context).
   - Avoid promotional language and dashes.

2) Key Quotes ("key_quotes")
   - Select between 1 and 5 short, representative quotes from the transcript.
   - Each quote should be meaningful on its own and useful as a call-out.
   - Keep the wording EXACTLY as spoken (verbatim, no edits).

3) Multiple-Choice ("mc_questions")
   - Create exactly {n_mcq} conceptual questions.
   - Each MCQ has a stem and exactly 4 choices labeled A–D.
   - Exactly ONE choice has "correct": true; the other three are false.
   - Question stems should be short and concise (roughly 1–2 sentences).
   - Provide explanatory "feedback" for the correct answer:
       • Feedback should be a longer explanation than the question stem
         (1–3 sentences of clarification).
       • Do NOT include the words "Correct" or "Incorrect" in the feedback text.
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
   - Each has a clear statement, a boolean "answer", and explanatory "feedback".
   - Statements should require reasoning, not recall of a single token or raw numbers.
   - Feedback should be 1–3 sentences that clarify *why* the statement is true or false.
   - Do NOT include the words "Correct" or "Incorrect" in the feedback text.

General formatting:
- Use standard ASCII quotes in JSON strings.
- Return ONLY JSON that conforms to the schema in the user message.
- No trailing commentary, no Markdown.

Self-check BEFORE replying:
- You have exactly {n_mcq} MCQs and exactly {n_tf} T/F items.
- "key_quotes" is an array with between 1 and 5 strings (each a verbatim quote).
- Every MCQ "choices" array has exactly 4 objects, labels are "A","B","C","D".
- Exactly one choice per MCQ has "correct": true (others false).
- All strings are valid JSON strings (ASCII quotes) and no extra fields are present.
If any check fails, fix your JSON and only then output it.
"""

USER_PROMPT = """\
Write {n_mcq} multiple-choice questions and {n_tf} true/false questions from this transcript.
Assume the learners are graduate-level students in a higher-education (university) program.

Transcript:
{transcript}

Output JSON object with this exact shape:
{{
  "intro": string,
  "key_quotes": [string, ...],
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
- "key_quotes" must be a non-empty array of between 1 and 5 strings.
- Exactly 4 choices per MCQ, labeled A–D.
- Exactly ONE choice per MCQ has "correct": true (others false).
- Question wording should be short and concise.
- Feedback must be a longer explanation (1–3 sentences) and must NOT
  contain the words "Correct" or "Incorrect".
- No “All of the above” or “None of the above”.
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
