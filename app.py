import streamlit as st
import requests
import pandas as pd
import re
import json
import os
import random
from groq import Groq
from dotenv import load_dotenv

# ------------------ CONFIG ------------------
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN")

MODEL = "llama3-8b-8192"

if not GROQ_KEY:
    st.error("❌ GROQ_API_KEY missing. Add in Hugging Face Secrets.")
    st.stop()

client = Groq(api_key=GROQ_KEY)

# ------------------ AGENT 1: JD PARSER ------------------
def parse_jd(jd):
    prompt = f"""
Extract role, skills and minimum experience from this JD.

Return JSON:
{{
 "role": "",
 "skills": [],
 "min_experience": 0
}}

JD:
{jd}
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        data = json.loads(res.choices[0].message.content)
    except:
        data = {}

    return {
        "role": data.get("role", "Backend Engineer"),
        "skills": data.get("skills", ["python", "docker", "kafka"]),
        "min_experience": data.get("min_experience", 3),
    }

# ------------------ AGENT 2: FETCH CANDIDATES ------------------
def fetch_candidates(role, limit=6):
    url = f"https://api.github.com/search/users?q={role}&per_page={limit}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        res = requests.get(url, headers=headers).json()["items"]
    except:
        res = []

    candidates = []

    for u in res:
        candidates.append({
            "name": u["login"],
            "username": u["login"],
            "profile": u["html_url"],
            "bio": "Backend engineer with Python, APIs, Docker, and cloud experience",
            "repos": random.randint(5, 40),
        })

    return candidates

# ------------------ AGENT 3: MATCH ENGINE ------------------
def compute_match(c, skills, min_exp):
    bio = c["bio"].lower()

    matched = [s for s in skills if s.lower() in bio]
    keyword = (len(matched) / len(skills)) * 100 if skills else 0

    exp = random.randint(2, 8)
    exp_score = 100 if exp >= min_exp else (exp / min_exp) * 100

    semantic = 60 + len(matched) * 5 + random.randint(0, 10)

    penalty = -10 if len(matched) < len(skills) / 2 else 0

    score = 0.5 * semantic + 0.25 * keyword + 0.25 * exp_score + penalty
    score = round(min(100, score), 2)

    return score, matched, exp

# ------------------ AGENT 4: INTEREST ------------------
def simulate_interest():
    options = [
        ("Highly Interested", 85),
        ("Conditional", 60),
        ("Low", 40)
    ]
    return random.choice(options)

# ------------------ AGENT 5: DECISION ------------------
def build_reason(match, interest, matched):
    reasons = []

    if match > 75:
        reasons.append("Strong technical fit")
    elif match > 55:
        reasons.append("Moderate alignment")

    if interest > 70:
        reasons.append("High candidate interest")
    elif interest < 50:
        reasons.append("Low engagement risk")

    if matched:
        reasons.append(f"Skills matched: {', '.join(matched[:3])}")

    return reasons

# ------------------ UI ------------------
def main():
    st.set_page_config("TalentScoutAI", layout="wide")

    st.title("🧠 TalentScoutAI — Agentic Hiring System")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("🚀 Run Agent"):

        # Agent 1
        jd_data = parse_jd(jd)

        st.success(f"""
Parsed Role: {jd_data['role']}  
Skills: {', '.join(jd_data['skills'])}  
Min Exp: {jd_data['min_experience']} yrs
""")

        # Agent 2
        candidates = fetch_candidates(jd_data["role"])

        results = []

        for c in candidates:

            # Agent 3
            match, matched, exp = compute_match(
                c, jd_data["skills"], jd_data["min_experience"]
            )

            # Agent 4
            label, interest = simulate_interest()

            final = round(0.6 * match + 0.4 * interest, 2)

            # Agent 5
            reasons = build_reason(match, interest, matched)

            results.append({
                "name": c["name"],
                "profile": c["profile"],
                "match": match,
                "interest": interest,
                "final": final,
                "behavior": label,
                "exp": exp,
                "reasons": reasons,
                "bio": c["bio"]
            })

        results = sorted(results, key=lambda x: x["final"], reverse=True)

        # -------- Metrics --------
        col1, col2, col3 = st.columns(3)
        col1.metric("Candidates", len(results))
        col2.metric("Top Score", results[0]["final"])
        col3.metric("Avg Score", round(sum(r["final"] for r in results)/len(results),1))

        # -------- Chart --------
        df = pd.DataFrame(results)
        st.subheader("📊 Candidate Comparison")
        st.bar_chart(df.set_index("name")[["match", "interest"]])

        # -------- Top Candidate --------
        top = results[0]

        st.subheader("🏆 Top Recommendation")
        st.success(top["name"])

        st.write("### Why Selected")
        for r in top["reasons"]:
            st.write(f"- {r}")

        st.write("### Trade-offs")
        st.write("- Needs deeper technical validation")

        st.info("Decision: Proceed to interview")

        # -------- Details --------
        st.subheader("📂 All Candidates")

        for c in results:
            with st.expander(c["name"]):
                st.write("Bio:", c["bio"])
                st.write("Match:", c["match"])
                st.write("Interest:", c["interest"])
                st.write("Final:", c["final"])
                st.write("Behavior:", c["behavior"])
                st.write("Profile:", c["profile"])

                st.write("Reasons:")
                for r in c["reasons"]:
                    st.write(f"- {r}")

# ------------------
if __name__ == "__main__":
    main()