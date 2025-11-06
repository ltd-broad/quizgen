# app.py
import os
from uuid import uuid4
import streamlit as st

from src.llm import get_quiz
from src.render import render_quiz_to_html

# ---------- Page config ----------
st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")
st.caption(
    "1) Generate a draft, 2) select which questions to keep, 3) get copy-pasteable HTML."
)


# ---------- Helpers ----------
def resolve_api_key(ui_input: str | None) -> str | None:
    """
    Priority: UI input > Streamlit Secrets > env var.
    Never crash if secrets.toml is missing.
    """
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
    # Clear any previous draft quiz + selection keys
    for k in list(st.session_state.keys()):
        if k.startswith("selns_"):  # checkbox keys live under this namespace
            del st.session_state[k]
    st.session_state.pop("quiz_draft", None)
    st.session_state.pop("sel_namespace", None)
    st.session_state.pop("final_html", None)


def get_tf_text(q) -> str:
    """Handle schema variations for TF question text."""
    return getattr(q, "text", getattr(q, "statement", getattr(q, "question", "")))


# ---------- API key (optional) ----------
api_key_input = st.text_input(
    "Optional: Override OpenAI API Key",
    type="password",
    placeholder="sk-...",
    help="Leave blank to use Streamlit Secrets or the OPENAI_API_KEY environment variable.",
)

# ---------- Question counts (dropdowns, no sliders) ----------
col1, col2 = st.columns(2)
with col1:
    n_mcq = st.selectbox(
        "Number of MCQs",
        options=list(range(1, 11)),  # 1..10
        index=1,  # default 2
        help="How many multiple-choice questions to generate in the draft.",
    )
with col2:
    n_tf = st.selectbox(
        "Number of True/False",
        options=list(range(1, 11)),  # 1..10
        index=1,  # default 2
        help="How many true/false questions to generate in the draft.",
    )

# ---------- Transcript input ----------
tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])
with tab_upload:
    uploaded = st.file_uploader("Choose a transcript (.txt)", type=["txt"])
with tab_paste:
    pasted = st.text_area("Or paste transcript text", height=220)

# Single primary action: toggles between Generate/Regenerate
has_draft = "quiz_draft" in st.session_state
action_label = "Regenerate draft" if has_draft else "Generate draft"
trigger_generate = st.button(action_label, type="primary")

# ---------- Step 1: Generate draft (one API call) ----------
if trigger_generate:
    # Clean previous session draft
    reset_draft_state()

    # Transcript
    transcript_text = None
    if uploaded is not None:
        transcript_text = read_uploaded_txt(uploaded)
    elif pasted and pasted.strip():
        transcript_text = pasted.strip()
    if not transcript_text:
        st.warning("Please upload a .txt file or paste transcript text.")
        st.stop()

    # API key
    api_key = resolve_api_key(api_key_input)
    if not api_key:
        st.warning(
            "No API key found. Enter one above, set it in Streamlit Secrets (deploy), "
            "or define OPENAI_API_KEY in your shell."
        )
        st.stop()

    # LLM call: single invoke to get the draft
    with st.spinner("Generating draft…"):
        try:
            quiz = get_quiz(transcript_text, n_mcq=n_mcq, n_tf=n_tf, api_key=api_key)
        except Exception as e:
            st.error(
                "The model call failed. Check your key, quota/billing, or try again."
            )
            st.exception(e)
            st.stop()

    # Store draft + a fresh selection namespace for checkbox keys
    st.session_state["quiz_draft"] = quiz
    st.session_state["sel_namespace"] = str(uuid4())

# ---------- Step 2: Review & select (no API calls) ----------
quiz = st.session_state.get("quiz_draft")
if quiz:
    st.markdown("### Step 2 — Review & select questions")
    st.caption("Uncheck any items you do not want to include in the final embed code.")

    ns = st.session_state["sel_namespace"]  # stable per generated draft

    # --- Multiple-Choice: checkbox + expander on the same row ---
    if getattr(quiz, "mc_questions", []):
        st.subheader("Multiple-Choice")
        for i, q in enumerate(quiz.mc_questions):
            col_cb, col_exp = st.columns([0.06, 0.94])

            with col_cb:
                st.checkbox(
                    f"Include MCQ {i+1}",
                    key=f"selns_{ns}_mc_{i}",
                    value=True,
                    help="Uncheck to exclude this question from the final HTML.",
                    label_visibility="collapsed",
                )

            with col_exp:
                # Expander header IS the question (chevron inline to its left)
                with st.expander(f"**Q{i+1}:** {q.question}", expanded=False):
                    for choice in q.choices:
                        st.write(f"- {choice.label}. {choice.text}")
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    # --- True / False: checkbox + expander on the same row ---
    if getattr(quiz, "tf_questions", []):
        st.subheader("True / False")
        for i, q in enumerate(quiz.tf_questions):
            tf_text = get_tf_text(q)

            col_cb, col_exp = st.columns([0.06, 0.94])

            with col_cb:
                st.checkbox(
                    f"Include T/F {i+1}",
                    key=f"selns_{ns}_tf_{i}",
                    value=True,
                    help="Uncheck to exclude this statement from the final HTML.",
                    label_visibility="collapsed",
                )

            with col_exp:
                # Expander header IS the statement
                with st.expander(f"**T/F {i+1}:** {tf_text}", expanded=False):
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    st.divider()
    make_html = st.button("Generate Embed HTML")

    if make_html:
        # Collect selections
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

        # Build a filtered quiz object of the same type
        try:
            filtered_quiz = type(quiz)(
                intro=getattr(quiz, "intro", ""),
                key_quote=getattr(quiz, "key_quote", ""),
                mc_questions=mc_keep,
                tf_questions=tf_keep,
            )
        except Exception as e:
            st.error(
                "Could not build the filtered quiz object. Check schema constraints."
            )
            st.exception(e)
            st.stop()

        # Render to HTML (no preview/download; just embed code)
        try:
            html_str = render_quiz_to_html(filtered_quiz)
            st.session_state["final_html"] = html_str
        except Exception as e:
            st.error("Failed to render HTML from the filtered quiz.")
            st.exception(e)
            st.stop()

# ---------- Step 3: Embed code ----------
final_html = st.session_state.get("final_html")
if final_html:
    st.markdown("### Step 3 — Embed code (copy & paste)")
    st.code(final_html, language="html")
    st.info(
        "Use the copy button in the code box, then paste into D2L: Insert Stuff → Enter Embed Code."
    )
