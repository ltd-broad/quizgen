# app.py
import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.llm import get_quiz
from src.render import render_quiz_to_html

# ---- Page config (title, wide) ----
st.set_page_config(page_title="QuizGen", layout="wide")  # docs: st.set_page_config
# ---- Header ----
st.title("QuizGen: Transcript → Interactive Quiz")
st.caption("Upload a transcript, optionally override the API key, and generate copy-pasteable HTML.")

# ---- Sidebar: API key handling ----
user_key = st.text_input("Optional: Override OpenAI API key", type="password").strip()

env_key = os.getenv("OPENAI_API_KEY", "").strip()

secrets_key = ""
try:
    # Only read secrets if a secrets file exists
    secrets_key = st.secrets["OPENAI_API_KEY"].strip()
except Exception:
    secrets_key = ""

api_key = (user_key or env_key or secrets_key)

if not api_key:
    st.warning("No API key available. Enter one above or set OPENAI_API_KEY in your env or .streamlit/secrets.toml.")
    st.stop()

# ---- Main: transcript input ----
tab_upload, tab_paste = st.tabs(["Upload .txt", "Paste text"])
transcript_text = ""

with tab_upload:
    up = st.file_uploader("Choose a transcript (.txt)", type=["txt"])  # docs: st.file_uploader
    if up is not None:
        # Streamlit keeps uploads in memory (BytesIO); decode to text
        transcript_text = up.read().decode("utf-8", errors="ignore")

with tab_paste:
    pasted = st.text_area("Paste transcript text here", height=300)
    if pasted:
        transcript_text = pasted

# Controls for counts (kept simple now; defaults per your current schema: 5 & 5)
st.sidebar.subheader("Generation options")
st.sidebar.write("Current prototype uses fixed 5 MCQ and 5 True/False as in your schema.")
generate_btn = st.button("Generate quiz")

# ---- Action ----
if generate_btn:
    if not transcript_text.strip():
        st.error("Please upload or paste a transcript before generating.")
        st.stop()

    # Run your existing pipeline (one call, no retries)
    quiz = get_quiz(transcript_text, api_key=api_key)  # we added api_key param earlier
    html_str = render_quiz_to_html(quiz)

    st.success("Quiz generated.")
    # Preview
    st.subheader("Preview")
    components.html(html_str, height=800, scrolling=True)

    # Embed code (copy/paste)
    st.subheader("Embed code (copy this into D2L → Insert Stuff → Enter Embed Code)")
    st.code(html_str, language="html")

    # Download button
    st.download_button(
        "Download HTML file",
        data=html_str.encode("utf-8"),
        file_name="quiz_output.html",
        mime="text/html",
    )

    st.info("Paste the code above into D2L: Insert Stuff → Enter Embed Code.")