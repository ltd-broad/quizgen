import os
from uuid import uuid4

import streamlit as st

from src.llm import get_quiz
from src.render import render_quiz_to_html

# ---------- Page config ----------
st.set_page_config(page_title="QuizGen", layout="wide")
st.title("QuizGen: Transcript ➜ Interactive Quiz")


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
        if k.startswith(
            "selns_"
        ):  # checkbox / selection keys live under this namespace
            del st.session_state[k]
    st.session_state.pop("quiz_draft", None)
    st.session_state.pop("sel_namespace", None)
    st.session_state.pop("final_html", None)
    st.session_state.pop("raw_transcript", None)
    st.session_state.pop("include_transcript", None)


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

# ---------- Transcript input + Step 1 ----------
st.markdown("### Step 1 — Provide transcript & generate draft")

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

    # Store transcript for possible inclusion in the final HTML
    st.session_state["raw_transcript"] = transcript_text

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
    st.markdown("### Step 2 — Review & select content")
    st.markdown(
        "Decide whether to include a transcript accordion, choose an optional key "
        "quote, then uncheck any questions you do not want to include in the "
        "final embed code."
    )

    # Transcript accordion toggle
    include_transcript = st.checkbox(
        "Include transcript accordion with transcript text",
        value=True,
        help=(
            "If checked, the embed HTML will include a collapsible 'Transcript' "
            "section showing the full transcript in a scrollable box."
        ),
    )
    st.session_state["include_transcript"] = include_transcript

    ns = st.session_state["sel_namespace"]  # stable per generated draft
    quote_sel_key = f"selns_{ns}_quote"

    # --- Key quote selection (at most one) ---
    if getattr(quiz, "key_quotes", []):
        st.subheader("Key quote")
        st.markdown(
            "Choose at most one quote to include in the final HTML (or **None**)."
        )

        quotes = quiz.key_quotes
        # We'll store the selected index as an int in session_state:
        #   0 => None
        #   1..N => pick quotes[index - 1]
        options_idx = list(range(len(quotes) + 1))

        def _format_quote_option(i: int) -> str:
            if i == 0:
                return "None (do not include a quote)"
            text = quotes[i - 1]
            # Shorten long quotes for the radio label
            if len(text) > 120:
                return f"“{text[:117]}...”"
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

    # ---------- Sequential question numbering ----------
    q_counter = 1  # Q1, Q2, ... across ALL question types

    # --- Multiple-Choice: checkbox + expander on the same row ---
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
                # Expander header IS the question (chevron inline to its left)
                with st.expander(f"**Q{qnum}:** {q.question}", expanded=False):
                    for choice in q.choices:
                        st.write(f"- {choice.label}. {choice.text}")
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    # --- True / False: checkbox + expander on the same row ---
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
                # Expander header IS the statement
                with st.expander(f"**Q{qnum}:** {tf_text}", expanded=False):
                    if getattr(q, "feedback", None):
                        st.write(f"**Feedback:** {q.feedback}")

    st.divider()

    # --- Centered Create / Clear buttons ---
    # Layout: [spacer] [Create Code] [Clear Code] [spacer]
    spacer_left, col_create, col_clear, spacer_right = st.columns([1, 0.6, 0.6, 1])

    with col_create:
        create_code_clicked = st.button(
            "Create Code", use_container_width=True, type="primary"
        )

    with col_clear:
        clear_code_clicked = st.button("Clear Code", use_container_width=True)

    # Handle Clear Code first (just wipes the generated HTML)
    if clear_code_clicked:
        st.session_state.pop("final_html", None)

    # Handle Create Code: generate filtered quiz + HTML
    if create_code_clicked:
        # Collect MCQ selections
        mc_keep = []
        for i, _ in enumerate(getattr(quiz, "mc_questions", [])):
            if st.session_state.get(f"selns_{ns}_mc_{i}", True):
                mc_keep.append(quiz.mc_questions[i])

        # Collect T/F selections
        tf_keep = []
        for i, _ in enumerate(getattr(quiz, "tf_questions", [])):
            if st.session_state.get(f"selns_{ns}_tf_{i}", True):
                tf_keep.append(quiz.tf_questions[i])

        if not mc_keep and not tf_keep:
            st.warning("You deselected all questions. Please include at least one.")
            st.stop()

        # Determine which key quote (if any) was selected
        quotes_list: list[str] = []
        if getattr(quiz, "key_quotes", []):
            quote_sel_key = f"selns_{ns}_quote"
            sel_idx = st.session_state.get(quote_sel_key, 0)
            if isinstance(sel_idx, int) and sel_idx > 0:
                idx = sel_idx - 1
                if 0 <= idx < len(quiz.key_quotes):
                    quotes_list = [quiz.key_quotes[idx]]

        # Transcript for HTML based on checkbox
        include_transcript = st.session_state.get("include_transcript", False)
        transcript_for_html = (
            st.session_state.get("raw_transcript", "") if include_transcript else ""
        )

        # Build a filtered quiz object of the same type
        try:
            filtered_quiz = type(quiz)(
                intro=getattr(quiz, "intro", ""),
                transcript=transcript_for_html,
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
        "Use the copy button in the code box, then paste into D2L: "
        "Insert Stuff → Enter Embed Code."
    )
