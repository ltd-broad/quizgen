import copy
import json
import random
import re
import html as html_lib
from uuid import uuid4

import streamlit as st

from src.llm import get_quiz
from src.render import render_quiz_to_html


st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")


def require_ui_api_key() -> str:
    """Require an instructor-provided API key (no secrets/env fallback)."""
    val = st.session_state.get("openai_api_key", "")
    key = val.strip() if isinstance(val, str) else ""
    return key


def read_uploaded_txt(file) -> str:
    """Read an uploaded .txt file robustly across Streamlit reruns."""
    try:
        file.seek(0)
    except Exception:
        pass

    try:
        data = file.read()
    except Exception:
        return ""

    if data is None:
        return ""

    if isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore").strip()

    return str(data).strip()


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


MODEL_OPTIONS = [
    "gpt-4.1",
    "o3-mini",
    "gpt-5.4",
    
]


st.markdown("### Step 1 — Provide transcript & generate draft")

try:
    step1_form = st.form("step1_form", border=False)
except TypeError:
    step1_form = st.form("step1_form")

with step1_form:
    st.text_input(
        "OpenAI API Key (Required)",
        key="openai_api_key",
        type="password",
        placeholder="sk-...",
        help="Enter your OpenAI API key",
    )
    tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])
    with tab_upload:
        uploaded = st.file_uploader("Choose a transcript (.txt)", type=["txt"])
    with tab_paste:
        pasted = st.text_area("Or paste transcript text", height=220)

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

    model_name = st.selectbox(
        "Model",
        options=MODEL_OPTIONS,
        index=0,
        help=(
            "Cost notes:\n\n"
            "- o3-mini can be about 2.7× higher cost than gpt-4.1-mini for similar token use.\n"
            "- Example: With an input of a 390-sentence transcript (about 7,800 words) and an output of an Introduction, a Quote, and about 20 knowledge-check questions, the cost is about \\$0.06 with o3-mini and about \\$0.02 with gpt-4.1-mini per run, based on current API pricing.\n"
            "- Track usage in your OpenAI dashboard: https://platform.openai.com/settings/organization/usage"
        ),
    )

    trigger_generate = st.form_submit_button("Generate draft", type="primary")


def _straighten_and_escape(s: str) -> str:
    """
    Convert curly quotes to straight quotes and HTML-escape content where appropriate.
    """
    if not s:
        return s
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return html_lib.escape(s)


def normalize_quiz_html(html: str) -> str:
    """
    Post-process the HTML produced by render_quiz_to_html to match formatting rules:
      - Remove literal "[embed video]" text, leaving an empty <p></p> placeholder.
      - Ensure quote is bold+italic with straight quotes inside a blockquote.
      - Ensure the full question text is bold (wrap <legend> contents in <strong>).
      - Keep feedback inside <details> unchanged.
      - Add a retry paragraph after the last </fieldset></section>.
    """
    if not html:
        return html

    out = html

    # 1) Remove any literal "[embed video]" text
    out = out.replace("[embed video]", "")
    out = re.sub(r'(?i)<p>\s*\[embed video\]\s*</p>', "<p></p>", out)

    # 2) Normalize blockquote content: ensure bold+italic with straight quotes
    def _format_blockquote(match):
        inner = match.group(1).strip()
        inner = _straighten_and_escape(inner)
        inner = inner.strip('"').strip()
        return (
            '<blockquote style="margin: 0 0 1.75rem 0;">'
            f'<strong><em>"{inner}"</em></strong>'
            "</blockquote>"
        )

    out = re.sub(
        r"<blockquote[^>]*>(.*?)</blockquote>",
        _format_blockquote,
        out,
        flags=re.DOTALL,
    )

    # 3) Ensure legend/question text is fully bold
    def _bold_legend(m):
        legend_content = m.group(1).strip()
        legend_content = re.sub(
            r"^<strong>(.*)</strong>$",
            r"\1",
            legend_content,
            flags=re.DOTALL,
        )
        return (
            '<legend style="margin-bottom: 0.25rem; font-weight: 400; font-family: inherit;">'
            f"<strong>{legend_content}</strong>"
            "</legend>"
        )

    out = re.sub(r"<legend[^>]*>(.*?)</legend>", _bold_legend, out, flags=re.DOTALL)

    # 4) Add retry note after the last </fieldset></section>
    marker = "</fieldset></section>"
    retry_html = "<p>You can refresh the page if you would like to try again.</p>"

    if marker in out and retry_html not in out:
        last_idx = out.rfind(marker)
        out = (
            out[: last_idx + len(marker)]
            + retry_html
            + out[last_idx + len(marker) :]
        )
    elif retry_html not in out:
        out += retry_html

    return out


def relabel_choices_a_to_d(mc_questions):
    """
    Relabel multiple-choice options sequentially as A, B, C, D... after shuffling.
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for q in mc_questions:
        choices = getattr(q, "choices", [])
        for idx, choice in enumerate(choices):
            if idx < len(letters):
                choice.label = letters[idx]

    return mc_questions


def shuffled_mc_questions(mc_questions):
    """
    Deep-copy MC questions, shuffle each question's choices, then relabel them A, B, C, D...
    This preserves randomized answer order while keeping clean visible labels.
    """
    shuffled_questions = []

    for q in mc_questions:
        q_copy = copy.deepcopy(q)
        choices = getattr(q_copy, "choices", [])

        if choices:
            random.shuffle(choices)
            q_copy.choices = choices

        shuffled_questions.append(q_copy)

    return relabel_choices_a_to_d(shuffled_questions)


if trigger_generate:
    reset_draft_state()

    api_key = require_ui_api_key()
    if not api_key:
        st.warning("Please enter your OpenAI API key above to continue.")
        st.stop()

    transcript_text: str | None = None
    has_upload = uploaded is not None
    has_paste = bool(pasted and pasted.strip())

    if has_upload:
        transcript_text = read_uploaded_txt(uploaded)
        if has_paste:
            st.info(
                "You provided both an uploaded .txt file and pasted text. "
                "Using the uploaded file. Clear it if you prefer the pasted text instead."
            )
    elif has_paste:
        transcript_text = pasted.strip()

    if not transcript_text:
        if has_upload and not has_paste:
            st.warning(
                "Your uploaded file appears empty or could not be read. "
                "Try re-uploading it or paste the text instead."
            )
        else:
            st.warning(
                "Please upload a .txt file or paste transcript text (but not both)."
            )
        st.stop()

    st.session_state["raw_transcript"] = transcript_text

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

    include_transcript_default = st.session_state.get(transcript_flag_key, False)
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
        selected_mc = []
        for i, q in enumerate(getattr(quiz, "mc_questions", [])):
            if st.session_state.get(f"selns_{ns}_mc_{i}", True):
                selected_mc.append(q)

        # Randomize selected MC answers, then relabel as A, B, C, D...
        mc_keep = shuffled_mc_questions(selected_mc)

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
            html_str = normalize_quiz_html(html_str)
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
    st.markdown(
        """
        <div style="font-size:1.1rem; font-weight:700; background-color:#F5F5DC; padding:0.75rem 1rem; border-radius:0.375rem;">
          Use the copy code button, then paste that into a D2L "Document Template" using Insert Stuff → Enter Embed Code.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.code(final_html, language="html")

