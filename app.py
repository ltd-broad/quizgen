# app.py
import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

from src.llm import get_quiz
from src.render import render_quiz_to_html


# ---------- Page config ----------
st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")
st.caption(
    "Upload a transcript, optionally override the API key, and generate copy-pasteable HTML."
)


# ---------- Helpers ----------
def resolve_api_key(ui_input: str | None) -> str | None:
    """
    Return OpenAI key with priority: UI input > Streamlit Secrets > env var.
    Never error if secrets.toml is missing.
    """
    # 1) UI field (masked)
    if ui_input and ui_input.strip():
        return ui_input.strip()

    # 2) Streamlit Secrets (handle secrets.toml not present)
    try:
        val = st.secrets["OPENAI_API_KEY"]  # raises if secrets.toml is missing
        if val:
            return str(val)
    except Exception:
        # Covers StreamlitSecretNotFoundError & any secrets parsing problems
        pass

    # 3) Shell environment variable
    val = os.getenv("OPENAI_API_KEY")
    if val:
        return val

    # 4) Nothing available
    return None


def read_uploaded_txt(file) -> str:
    """Decode a .txt upload to UTF-8 text."""
    try:
        return file.read().decode("utf-8")
    except Exception:
        # Fall back if already str-like
        return file.read()


# ---------- UI ----------
api_key_input = st.text_input(
    "Optional: Override OpenAI API Key",
    type="password",
    placeholder="sk-...",
    help="Leave blank to use Streamlit Secrets or the OPENAI_API_KEY environment variable.",
)

tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])

with tab_upload:
    uploaded = st.file_uploader("Choose a transcript (.txt)", type=["txt"])

with tab_paste:
    pasted = st.text_area("Or paste transcript text", height=220)

generate = st.button("Generate quiz", type="primary")


# ---------- Main action ----------
if generate:
    # 1) Read transcript
    transcript_text = None
    if uploaded is not None:
        transcript_text = read_uploaded_txt(uploaded)
    elif pasted and pasted.strip():
        transcript_text = pasted.strip()

    if not transcript_text:
        st.warning("Please upload a .txt file or paste transcript text.")
        st.stop()

    # 2) Resolve the API key (optional UI → secrets → env)
    api_key = resolve_api_key(api_key_input)
    if not api_key:
        st.warning(
            "No API key found. Enter one above, set it in Streamlit Secrets (deploy), "
            "or define OPENAI_API_KEY in your shell."
        )
        st.stop()

    # 3) Call the model once (no hidden retries)
    with st.spinner("Generating quiz…"):
        try:
            quiz = get_quiz(transcript_text, api_key=api_key)   # one call
        except Exception as e:
            st.error(
                "The model call failed. Please check your API key, quota/billing, or try again."
            )
            st.exception(e)
            st.stop()

    # 4) Render to HTML
    try:
        html_str = render_quiz_to_html(quiz)
    except Exception as e:
        st.error("Failed to render HTML from the model output.")
        st.exception(e)
        st.stop()

    # 5) Present **copy-paste code FIRST**
    st.subheader("Embed code (copy & paste)")
    st.code(html_str, language="html")

    st.download_button(
        "Download HTML",
        data=html_str.encode("utf-8"),
        file_name="quiz_output.html",
        mime="text/html",
        use_container_width=True,
    )

    # 6) Live **preview** of the HTML
    st.subheader("Preview")
    components.html(html_str, height=800, scrolling=True)