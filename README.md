QuizGen

QuizGen is a Streamlit application that takes a lecture transcript, sends it to an OpenAI model, and generates a structured quiz (multiple-choice and true/false).
The instructor can review the generated questions, select which ones to include, and export clean HTML to paste directly into D2L.

⸻

Features
	•	Upload or paste transcript text
	•	Choose number of MCQs and True/False questions
	•	Switch between OpenAI models (gpt-4.1-mini and o3-mini)
	•	LLM pipeline with automatic JSON repair and validation
	•	Instructor can select which questions to keep
	•	Generates D2L-ready HTML via a Jinja template
	•	Web UI using Streamlit

⸻

Model Cost Notes

The app includes two OpenAI models:
	•	gpt-4.1-mini
Approx. $0.40 per 1M input tokens and $1.60 per 1M output tokens 
	•	o3-mini (reasoning model)
Approx. $1.10 per 1M input tokens and $4.40 per 1M output tokens 

In practice, quiz runs usually cost only a few cents unless the transcript is very long.
https://platform.openai.com/settings/organization/usage

⸻

Tech Stack and Python Version
	•	Python 3.11
	•	Streamlit for UI
	•	OpenAI Python SDK
	•	LangChain for message building
	•	Pydantic for validation
	•	Jinja2 for HTML template rendering

The project includes:
	•	requirements.txt (pip dependencies)
	•	environment.yml (Conda environment, Python 3.11)

Important: When deploying to Streamlit Community Cloud, set the Python version to 3.11 under “Advanced settings”.

⸻

Local Setup

1. Clone the repository

git clone https://github.com/<your-username>/quizgen.git
cd quizgen

If using the original repository, fork it first on GitHub, then clone your own fork.

2. Create and activate a Python 3.11 environment

Using Conda:

conda env create -f environment.yml
conda activate quizgen

Or using venv:

python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

3. Set the OpenAI API key

You may provide your API key in any of these ways:
	1.	Enter it directly in the UI field (“Override OpenAI API Key”)
	2.	Environment variable:

export OPENAI_API_KEY="sk-..."


	3.	Streamlit secrets (local):
Create .streamlit/secrets.toml:

OPENAI_API_KEY = "sk-..."



4. Run the app

streamlit run app.py


⸻

Deploying on Streamlit Community Cloud

1. Requirements
	•	GitHub account
	•	Streamlit Community Cloud account
	•	Your own copy of the code (fork or private repo)

2. Deploy
	1.	Go to https://share.streamlit.io
	2.	Click “New app”
	3.	Connect GitHub if prompted
	4.	Choose your repo and branch
	5.	Set entrypoint to app.py

3. Set the Python version

In “Advanced settings”:
	•	Choose Python 3.11

4. Add API key to Streamlit secrets

In the “Secrets” section:

OPENAI_API_KEY = "sk-..."

5. Deploy

Streamlit builds the environment and gives you a public URL.
Any time you push changes, redeploy from the dashboard.

⸻

Project Structure

quizgen/
  app.py                     # Streamlit UI and main flow
  environment.yml            # Conda environment (Python 3.11)
  requirements.txt           # pip dependencies
  src/
    llm.py                   # LLM pipeline: prompt → JSON → quiz object
    prompts.py               # System and user prompts
    schemas.py               # Pydantic models defining Quiz structure
    utils.py                 # Output repair helpers
    render.py                # Renders Quiz → HTML (Jinja template)
  templates/
    quiz_spartan.html.j2     # HTML template for D2L output
  .streamlit/
    secrets.toml (optional)  # Local secrets, not committed


⸻

How the Flow Works
	1.	Instructor provides transcript and selects question counts and model.
	2.	app.py calls get_quiz() in llm.py.
	3.	llm.py:
	•	Builds system + user prompts
	•	Calls the OpenAI API
	•	Repairs common JSON issues
	•	Validates via Pydantic Quiz model
	4.	A valid Quiz object is returned to app.py.
	5.	Instructor selects which questions to include.
	6.	render.py generates D2L-compatible HTML via Jinja.
	7.	App displays final HTML for copy-paste.

⸻

Customisation
	•	Change quiz appearance:
templates/quiz_spartan.html.j2
	•	Change quiz rules or schema:
src/prompts.py, src/schemas.py
	•	Add or modify models:
Update model dropdown in app.py and logic in src/llm.py

⸻

Notes
	•	Costs depend on transcript length, model choice, and number of questions
	•	Always store API keys in secrets, not in code
	•	Ensure Python version matches between local and Streamlit Cloud

⸻
