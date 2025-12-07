import os
import json
from uuid import uuid4

import streamlit as st

from src.llm import get_quiz
from src.render import render_quiz_to_html


st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")


def resolve_api_key(ui_input: str | None) -> str | None:
    if ui_input and ui_input.strip():
        return ui_input.strip()

    try:
        val = st.secrets["OPENAI_API_KEY"]
        if val:
            return str(val)
    except Exception:
        pass

    val = os.getenv("OPENAI_API_KEY")
    if val:
        return val

    return None


def read_uploaded_txt(file) -> str:
    try:
        return file.read().decode("utf-8")
    except Exception:
        return file.read()


def reset_draft_state():
    for k in list(st.session_state.keys()):
        if k.startswith("selns_"):
            del st.session_state[k]

    st.session_state.pop("quiz_draft", None)
    st.session_state.pop("sel_namespace", None)
    st.session_state.pop("final_html", None)
    st.session_state.pop("raw_transcript", None)


def get_tf_text(q) -> str:
    return getattr(q, "text", getattr(q, "statement", getattr(q, "question", "")))


api_key_input = st.text_input(
    "Optional: Override OpenAI API Key",
    type="password",
    placeholder="sk-...",
    help="Leave blank to use Streamlit Secrets or the OPENAI_API_KEY environment variable.",
)


MODEL_OPTIONS = [
    "gpt-4.1-mini",
    "o3-mini",
]

model_name = st.selectbox(
    "Model",
    options=MODEL_OPTIONS,
    index=0,
    help="Switch models for draft generation.",
)


col1, col2 = st.columns(2)
with col1:
    n_mcq = st.selectbox(
        "Number of MCQs",
        options=list(range(1, 11)),
        index=1,
        help="How many multiple-choice questions to generate in the draft.",
    )
with col2:
    n_tf = st.selectbox(
        "Number of True/False",
        options=list(range(1, 11)),
        index=1,
        help="How many true/false questions to generate in the draft.",
    )


st.markdown("### Step 1 — Provide transcript & generate draft")

tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])
with tab_upload:
    uploaded = st.file_uploader("Choose a transcript (.txt)", type=["txt"])
with tab_paste:
    pasted = st.text_area("Or paste transcript text", height=220)

has_draft = "quiz_draft" in st.session_state
action_label = "Regenerate draft" if has_draft else "Generate draft"
trigger_generate = st.button(action_label, type="primary")


if trigger_generate:
    reset_draft_state()

    transcript_text: str | None = None
    both_provided = uploaded is not None and pasted and pasted.strip()

    if uploaded is not None:
        transcript_text = read_uploaded_txt(uploaded)
        if both_provided:
            st.info(
                "You provided both an uploaded .txt file and pasted text. "
                "Using the uploaded file. Clear it if you prefer the pasted text instead."
            )
    elif pasted and pasted.strip():
        transcript_text = pasted.strip()

    if not transcript_text:
        st.warning("Please upload a .txt file or paste transcript text (but not both).")
        st.stop()

    st.session_state["raw_transcript"] = transcript_text

    api_key = resolve_api_key(api_key_input)
    if not api_key:
        st.warning(
            "No API key found. Enter one above, set it in Streamlit Secrets (deploy), "
            "or define OPENAI_API_KEY in your shell."
        )
        st.stop()

    with st.spinner("Generating draft…"):
        try:
            quiz = get_quiz(
                transcript_text,
                n_mcq=n_mcq,
                n_tf=n_tf,
                api_key=api_key,
                model_name=model_name,
            )
        except Exception as e:
            st.error(
                "The model call failed. Check your key, quota/billing, or try again."
            )
            st.exception(e)
            st.stop()

    st.session_state["quiz_draft"] = quiz
    st.session_state["sel_namespace"] = str(uuid4())


quiz = st.session_state.get("quiz_draft")
if quiz:
    st.markdown("### Step 2 — Review & select content")
    st.markdown(
        "Decide whether to include an introduction and transcript accordion, "
        "optionally pick a key quote, then uncheck any questions you do not want "
        "to include in the final embed code."
    )

    ns = st.session_state["sel_namespace"]
    quote_sel_key = f"selns_{ns}_quote"
    transcript_flag_key = f"selns_{ns}_include_transcript"
    intro_flag_key = f"selns_{ns}_include_intro"

    include_intro_default = st.session_state.get(intro_flag_key, True)
    st.checkbox(
        "Include introduction",
        key=intro_flag_key,
        value=include_intro_default,
        help="Adds an 'Introduction' heading and the intro sentence above the embed video.",
    )

    include_transcript_default = st.session_state.get(transcript_flag_key, True)
    st.checkbox(
        "Include transcript accordion with transcript text",
        key=transcript_flag_key,
        value=include_transcript_default,
        help=(
            "Adds a collapsible 'Transcript' section to the generated HTML so "
            "students can expand it to read the full transcript."
        ),
    )

    if getattr(quiz, "key_quotes", []):
        st.subheader("Key quote")
        st.markdown("Choose at most one quote to include in the final HTML (or None).")

        quotes = quiz.key_quotes
        options_idx = list(range(len(quotes) + 1))

        def _format_quote_option(i: int) -> str:
            if i == 0:
                return "None (do not include a quote)"
            text = quotes[i - 1]
            if len(text) > 140:
                return f"“{text[:137]}...”"
            return f"“{text}”"

        current_idx = st.session_state.get(quote_sel_key, 0)
        if current_idx >= len(options_idx):
            current_idx = 0

        selected_idx = st.radio(
            "Select key quote for embed:",
            options=options_idx,
            index=current_idx,
            format_func=_format_quote_option,
        )
        st.session_state[quote_sel_key] = selected_idx

    q_counter = 1

    if getattr(quiz, "mc_questions", []):
        st.subheader("Multiple-Choice")
        for i, q in enumerate(quiz.mc_questions):
            qnum = q_counter
            q_counter += 1

            col_cb, col_exp = st.columns([0.06, 0.94])

            with col_cb:
                st.checkbox(
                    f"Include Q{qnum}",
                    key=f"selns_{ns}_mc_{i}",
                    value=True,
                    help="Uncheck to exclude this question from the final HTML.",
                    label_visibility="collapsed",
                )

            with col_exp:
                with st.expander(f"**Q{qnum}:** {q.question}", expanded=False):
                    for choice in q.choices:
                        st.write(f"- {choice.label}. {choice.text}")
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    if getattr(quiz, "tf_questions", []):
        st.subheader("True / False")
        for i, q in enumerate(quiz.tf_questions):
            tf_text = get_tf_text(q)
            qnum = q_counter
            q_counter += 1

            col_cb, col_exp = st.columns([0.06, 0.94])

            with col_cb:
                st.checkbox(
                    f"Include Q{qnum}",
                    key=f"selns_{ns}_tf_{i}",
                    value=True,
                    help="Uncheck to exclude this statement from the final HTML.",
                    label_visibility="collapsed",
                )

            with col_exp:
                with st.expander(f"**Q{qnum}:** {tf_text}", expanded=False):
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    st.divider()

    spacer_left, col_create, col_copy, col_clear, spacer_right = st.columns(
        [1, 0.8, 0.8, 0.8, 1]
    )

    with col_create:
        create_code_clicked = st.button(
            "Create Code", use_container_width=True, type="primary"
        )

    with col_copy:
        copy_placeholder = st.empty()

    with col_clear:
        clear_code_clicked = st.button("Clear Code", use_container_width=True)

    if clear_code_clicked:
        st.session_state.pop("final_html", None)

    if create_code_clicked:
        mc_keep = []
        for i, _ in enumerate(getattr(quiz, "mc_questions", [])):
            if st.session_state.get(f"selns_{ns}_mc_{i}", True):
                mc_keep.append(quiz.mc_questions[i])

        tf_keep = []
        for i, _ in enumerate(getattr(quiz, "tf_questions", [])):
            if st.session_state.get(f"selns_{ns}_tf_{i}", True):
                tf_keep.append(quiz.tf_questions[i])

        if not mc_keep and not tf_keep:
            st.warning("You deselected all questions. Please include at least one.")
            st.stop()

        quotes_list: list[str] = []
        if getattr(quiz, "key_quotes", []):
            sel_idx = st.session_state.get(quote_sel_key, 0)
            if isinstance(sel_idx, int) and sel_idx > 0:
                idx = sel_idx - 1
                if 0 <= idx < len(quiz.key_quotes):
                    quotes_list = [quiz.key_quotes[idx]]

        include_transcript_flag = bool(st.session_state.get(transcript_flag_key, False))
        include_intro_flag = bool(st.session_state.get(intro_flag_key, True))
        raw_transcript = st.session_state.get("raw_transcript", "")

        intro_text = getattr(quiz, "intro", "") if include_intro_flag else ""

        try:
            filtered_quiz = type(quiz)(
                intro=intro_text,
                key_quotes=quotes_list,
                mc_questions=mc_keep,
                tf_questions=tf_keep,
            )
        except Exception as e:
            st.error(
                "Could not build the filtered quiz object. Check schema constraints."
            )
            st.exception(e)
            st.stop()

        try:
            html_str = render_quiz_to_html(
                filtered_quiz,
                raw_transcript,
                include_transcript_flag,
                include_intro_flag,
            )
            st.session_state["final_html"] = html_str
        except Exception as e:
            st.error("Failed to render HTML from the filtered quiz.")
            st.exception(e)
            st.stop()

    final_html_for_copy = st.session_state.get("final_html")
    has_code = bool(final_html_for_copy)
    payload = json.dumps(final_html_for_copy) if has_code else json.dumps("")
    disabled_attr = "" if has_code else "disabled"

    with copy_placeholder:
        try:
            st.components.v1.html(
                f"""
                <style>
                  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600&display=swap');
                  html, body {{
                    margin: 0;
                    padding: 0;
                    font-family: "Source Sans 3", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                  }}
                  .copy-btn {{
                    width: 100%;
                    min-height: 2.5rem;
                    padding: 0.5rem 0.75rem;
                    border-radius: 0.5rem;
                    border: 1px solid transparent;
                    background: #008001;
                    color: #ffffff;
                    font-size: 1rem;
                    font-weight: 500;
                    font-family: inherit;
                    line-height: 1.2;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                    text-rendering: optimizeLegibility;
                    cursor: pointer;
                    white-space: nowrap;
                  }}
                  .copy-btn:hover {{ filter: brightness(0.98); }}
                  .copy-btn:active, .copy-btn:focus {{ outline: none; }}
                  .copy-btn[disabled] {{
                    background: #f3f4f6;
                    color: #9ca3af;
                    border: 1px solid #d0d0d0;
                    cursor: not-allowed;
                    filter: none;
                  }}
                </style>
                <button id='copy-embed-code-top' class='copy-btn' {disabled_attr}>Copy Code</button>
                <script>
                  const text = {payload};
                  const btn = document.getElementById('copy-embed-code-top');

                  const resetLabel = () => {{ btn.textContent = 'Copy Code'; }};

                  btn.addEventListener('click', async () => {{
                    if (btn.hasAttribute('disabled')) return;
                    try {{
                      await navigator.clipboard.writeText(text);
                      btn.textContent = 'Copied';
                      setTimeout(resetLabel, 1200);
                    }} catch (e) {{
                      btn.textContent = 'Copy failed';
                      setTimeout(resetLabel, 1200);
                    }}
                  }});
                </script>
                """,
                height=70,
                scrolling=False,
            )
        except Exception:
            st.button("Copy Code", use_container_width=True, disabled=True)


final_html = st.session_state.get("final_html")
if final_html:
    st.markdown("### Step 3 — Embed code (copy & paste)")
    st.info(
        "Use the copy button on the right side of the embed code box, then paste that "
        "HTML into D2L using Insert Stuff → Enter Embed Code."
    )
    st.code(final_html, language="html")
