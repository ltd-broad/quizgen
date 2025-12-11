# QuizGen

QuizGen is a Streamlit application that takes a lecture transcript, sends it to an OpenAI model, and generates a structured quiz (multiple-choice and true/false).  
The instructor can review the generated questions, select which ones to include, and export clean HTML to paste directly into D2L.

---

## Features

- Upload or paste transcript text  
- Choose number of MCQs and True/False questions  
- Switch between OpenAI models (gpt-4.1-mini and o3-mini)  
- LLM pipeline with automatic JSON repair and validation  
- Instructor can select which questions to keep  
- Generates D2L-ready HTML via a Jinja template  
- Streamlit web UI  

---

## Model Cost Notes

The app includes two OpenAI models:

### gpt-4.1-mini  
Approx. **$0.40 per 1M input tokens** and **$1.60 per 1M output tokens**  
(Always verify with OpenAI’s pricing page.)

### o3-mini (reasoning model)  
Approx. **$1.10 per 1M input tokens** and **$4.40 per 1M output tokens**  
(Always verify with OpenAI’s pricing page.)

In practice, quiz runs usually cost only a few cents unless the transcript is very long.

---

## Tech Stack and Python Version

- Python **3.11**  
- Streamlit  
- OpenAI Python SDK  
- LangChain  
- Pydantic  
- Jinja2  

Project includes:

- `requirements.txt`  
- `environment.yml`  

**Important:** When deploying to Streamlit Community Cloud, set Python version to **3.11** under *Advanced settings*.

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/quizgen.git
cd quizgen
```

If using the original repository, fork it first on GitHub and then clone your fork.

---

### 2. Create and activate a Python 3.11 environment

**Conda:**

```bash
conda env create -f environment.yml
conda activate quizgen
```

**venv:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Set the OpenAI API key

You may provide your API key in one of these ways:

#### A. Enter directly in the UI  
Use the “Override OpenAI API Key” field.

#### B. Environment variable

```bash
export OPENAI_API_KEY="sk-..."
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

#### C. Streamlit secrets (local)

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
```

---

### 4. Run the app

```bash
streamlit run app.py
```

---

## Deploying on Streamlit Community Cloud

### 1. Requirements

- GitHub account  
- Streamlit Community Cloud account  
- Your own repo (fork or copy)

---

### 2. Deploy the app

1. Go to https://share.streamlit.io  
2. Click **New app**  
3. Connect GitHub if asked  
4. Pick your repo & branch  
5. Set entrypoint to `app.py`

---

### 3. Set the Python version

In **Advanced settings**, choose:

```
Python 3.11
```

---

### 4. Add the API key in Streamlit Secrets

In the Secrets editor:

```toml
OPENAI_API_KEY = "sk-..."
```

---

### 5. Deploy

Streamlit builds your environment and gives you a public link.  
Redeploy any time you push new changes.

---

## Project Structure

```text
quizgen/
  app.py                     # Streamlit UI and main flow
  environment.yml            # Conda environment (Python 3.11)
  requirements.txt           # Dependencies
  src/
    llm.py                   # LLM pipeline: prompt → JSON → Quiz
    prompts.py               # System + user prompts
    schemas.py               # Quiz Pydantic models
    utils.py                 # Output repair helpers
    render.py                # Quiz → HTML via Jinja
  templates/
    quiz_spartan.html.j2     # HTML template for D2L
  .streamlit/
    secrets.toml (optional)  # Local secrets
```

---

## How the Flow Works

1. Instructor provides transcript and selects counts / model  
2. `app.py` calls `get_quiz()`  
3. `llm.py`  
   - Builds prompts  
   - Calls OpenAI  
   - Repairs JSON  
   - Validates using `Quiz` schema  
4. Returns a valid `Quiz` object  
5. Instructor selects which questions to keep  
6. `render.py` generates D2L-ready HTML  
7. App displays final HTML  

---

## Customisation

- Modify HTML output → `templates/quiz_spartan.html.j2`  
- Modify quiz rules or schema → `src/prompts.py`, `src/schemas.py`  
- Add/modify models → update dropdown in `app.py` and logic in `llm.py`  

---

## Notes

- Cost depends on transcript length, model choice, and question count  
- Never store API keys in code  
- Ensure Streamlit Cloud uses Python 3.11  
