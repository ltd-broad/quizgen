# app.py
import os
import streamlit as st

from src.llm import get_quiz
from src.render import render_quiz_to_html

# ---------- Page config ----------
st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")
st.caption(
    "Upload a transcript, choose how many questions to generate, optionally override the API key, and get copy-pasteable HTML."
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
        options=list(range(1, 11)),   # 1..10
        index=1,                      # default 2
        help="How many multiple-choice questions to generate.",
    )
with col2:
    n_tf = st.selectbox(
        "Number of True/False",
        options=list(range(1, 11)),   # 1..10
        index=1,                      # default 2
        help="How many true/false questions to generate.",
    )

# ---------- Transcript input ----------
tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])
with tab_upload:
    uploaded = st.file_uploader("Choose a transcript (.txt)", type=["txt"])
with tab_paste:
    pasted = st.text_area("Or paste transcript text", height=220)

generate = st.button("Generate quiz", type="primary")

# ---------- Main action ----------
if generate:
    # 1) Transcript
    transcript_text = None
    if uploaded is not None:
        transcript_text = read_uploaded_txt(uploaded)
    elif pasted and pasted.strip():
        transcript_text = pasted.strip()
    if not transcript_text:
        st.warning("Please upload a .txt file or paste transcript text.")
        st.stop()

    # 2) API key resolution
    api_key = resolve_api_key(api_key_input)
    if not api_key:
        st.warning(
            "No API key found. Enter one above, set it in Streamlit Secrets (deploy), "
            "or define OPENAI_API_KEY in your shell."
        )
        st.stop()

    # 3) LLM call (single invoke)
    with st.spinner("Generating quiz…"):
        try:
            quiz = get_quiz(transcript_text, n_mcq=n_mcq, n_tf=n_tf, api_key=api_key)
        except Exception as e:
            st.error("The model call failed. Check your key, quota/billing, or try again.")
            st.exception(e)
            st.stop()

    # 4) Render HTML
    try:
        html_str = render_quiz_to_html(quiz)
    except Exception as e:
        st.error("Failed to render HTML from the model output.")
        st.exception(e)
        st.stop()

    # 5) Embed code only (no download/preview)
    st.subheader("Embed code (copy & paste)")
    st.code(html_str, language="html")
    st.info(
        "Use the copy button in the code box, then paste into D2L: "
        "Insert Stuff → Enter Embed Code."
    )