# Catalyst AI Talent Scouting Agent

## Setup
1. Clone repo, create venv, `pip install -r requirements.txt`
2. Create `.env` with `GROQ_API_KEY=your_key`
3. `streamlit run app.py`

## Features
- Parses JD with Groq (llama-3.1)
- Finds real GitHub profiles (optional location filter)
- Enriches with Stack Overflow reputation
- Hybrid match score (semantic + keyword + experience + SO bonus)
- Personalized icebreaker from candidate’s last commit
- Two‑turn conversation + sentiment interest scoring
- Ranked shortlist, explainability, CSV export

## Deploy to Streamlit Cloud
- Push to GitHub, set `GROQ_API_KEY` as secret, deploy.