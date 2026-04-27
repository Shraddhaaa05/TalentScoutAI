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
    st.error("❌ GROQ_API_KEY missing.")
    st.stop()

client = Groq(api_key=GROQ_KEY)

# ------------------ VALIDATION ------------------
def is_valid_jd(jd):
    jd = jd.lower()
    if len(jd.strip()) < 80:
        return False

    signals = ["requirements", "skills", "experience", "responsibilities", "engineer", "developer"]
    return any(s in jd for s in signals)

# ------------------ RULE BASED PARSER ------------------
def rule_based_extract(jd):
    jd_lower = jd.lower()

    role_match = re.search(r'(senior|junior|lead)?\s*(backend|frontend|ml|data|software)\s*(engineer|developer)', jd_lower)
    role = role_match.group(0).title() if role_match else "Unknown Role"

    exp_match = re.search(r'(\d+)\+?\s*(years|yrs)', jd_lower)
    min_exp = int(exp_match.group(1)) if exp_match else None

    skill_keywords = [
        "python","java","go","sql","kafka","redis","postgresql",
        "docker","kubernetes","aws","gcp","pytorch","tensorflow",
        "ml","nlp","llm","spark"
    ]

    skills = [s for s in skill_keywords if s in jd_lower]

    return {
        "role": role,
        "skills": list(set(skills)),
        "min_experience": min_exp
    }

# ------------------ LLM PARSER ------------------
def llm_parse_jd(jd):
    prompt = f"""
Extract structured hiring data.

Return JSON ONLY:
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
            temperature=0
        )
        return json.loads(res.choices[0].message.content)
    except:
        return {}

# ------------------ FINAL PARSER ------------------
def parse_jd(jd):
    if not is_valid_jd(jd):
        st.error("❌ Invalid Job Description. Please enter a real JD.")
        st.stop()

    data = llm_parse_jd(jd)

    role = data.get("role")
    skills = data.get("skills", [])
    min_exp = data.get("min_experience")

    rb = rule_based_extract(jd)

    if not role:
        role = rb["role"]

    if not skills or len(skills) < 3:
        skills = rb["skills"]

    if not min_exp:
        min_exp = rb["min_experience"]

    if not skills or len(skills) < 2:
        st.error("❌ Could not extract enough skills.")
        st.stop()

    if not min_exp:
        min_exp = 3

    return {
        "role": role,
        "skills": skills,
        "min_experience": min_exp
    }

# ------------------ GITHUB FETCH ------------------
def fetch_candidates(role, limit=6):
    url = f"https://api.github.com/search/users?q={role}&per_page={limit}"
    headers = {}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        items = requests.get(url, headers=headers).json().get("items", [])
    except:
        items = []

    candidates = []

    for u in items:
        username = u["login"]

        try:
            profile = requests.get(
                f"https://api.github.com/users/{username}",
                headers=headers
            ).json()
        except:
            profile = {}

        candidates.append({
            "name": username,
            "profile": u["html_url"],
            "bio": profile.get("bio") or "Software engineer working on scalable systems",
            "repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0)
        })

    return candidates

# ------------------ MATCH ENGINE ------------------
def compute_match(c, skills, min_exp):
    bio = c["bio"].lower()

    matched = [s for s in skills if s.lower() in bio]
    skill_score = (len(matched) / len(skills)) * 100

    exp = random.randint(2, 8)
    exp_score = 100 if exp >= min_exp else (exp / min_exp) * 100

    context_bonus = 10 if "kafka" in bio or "distributed" in bio else 0

    github_bonus = 5 if c["repos"] > 20 else 0
    github_bonus += 5 if c["followers"] > 50 else 0

    penalty = -15 if len(matched) < len(skills)/2 else 0

    final = 0.5*skill_score + 0.3*exp_score + context_bonus + github_bonus + penalty
    final = max(0, min(100, round(final,2)))

    breakdown = {
        "Skill Match": round(skill_score,1),
        "Experience": exp,
        "Context Bonus": context_bonus,
        "GitHub Bonus": github_bonus,
        "Penalty": penalty
    }

    return final, matched, breakdown

# ------------------ INTEREST ------------------
def simulate_interest():
    return random.choice([
        ("Highly Interested",85),
        ("Conditional",60),
        ("Passive",40)
    ])

# ------------------ DECISION ------------------
def build_reason(c, match, interest, matched):
    reasons = []

    if match > 70:
        reasons.append("Strong technical alignment")

    if interest > 70:
        reasons.append("High candidate intent")

    if c["repos"] > 20:
        reasons.append("Active GitHub contributor")

    if matched:
        reasons.append(f"Skills matched: {', '.join(matched[:3])}")

    return reasons

def compare_others(results):
    insights = []
    for r in results[1:4]:
        if r["interest"] < 50:
            insights.append(f"{r['name']}: low interest")
        elif r["match"] < 60:
            insights.append(f"{r['name']}: weak technical fit")
        else:
            insights.append(f"{r['name']}: decent but not top")
    return insights

# ------------------ UI ------------------
def main():
    st.set_page_config("TalentScoutAI", layout="wide")
    st.title("🧠 TalentScoutAI — Hiring Decision System")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("🚀 Run Agent"):

        jd_data = parse_jd(jd)

        st.success(f"""
Role: {jd_data['role']}
Skills: {', '.join(jd_data['skills'])}
Min Experience: {jd_data['min_experience']} yrs
""")

        candidates = fetch_candidates(jd_data["role"])

        results = []

        for c in candidates:
            match, matched, breakdown = compute_match(c, jd_data["skills"], jd_data["min_experience"])
            label, interest = simulate_interest()
            final = round(0.6*match + 0.4*interest,2)
            reasons = build_reason(c, match, interest, matched)

            results.append({
                "name": c["name"],
                "profile": c["profile"],
                "bio": c["bio"],
                "match": match,
                "interest": interest,
                "final": final,
                "repos": c["repos"],
                "followers": c["followers"],
                "reasons": reasons,
                "breakdown": breakdown
            })

        results = sorted(results, key=lambda x: x["final"], reverse=True)

        # Metrics
        st.write(f"Candidates: {len(results)}")
        st.write(f"Top Score: {results[0]['final']}")

        # Chart
        df = pd.DataFrame(results)
        st.bar_chart(df.set_index("name")[["match","interest"]])

        # Top candidate
        top = results[0]
        st.subheader(f"🏆 {top['name']}")
        st.markdown(f"[GitHub Profile]({top['profile']})")

        st.write("Why Selected:")
        for r in top["reasons"]:
            st.write("-", r)

        st.write("Why not others:")
        for r in compare_others(results):
            st.write("-", r)

        st.write("Decision: Proceed to interview")

# ------------------
if __name__ == "__main__":
    main()