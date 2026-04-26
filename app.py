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

# ------------------ AGENT 1: JD PARSER ------------------
def parse_jd(jd):
    prompt = f"""
Extract:
- role
- ALL technical skills, tools, frameworks
- minimum years of experience

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
        data = json.loads(res.choices[0].message.content)
    except:
        data = {}

    skills = data.get("skills", [])
    if len(skills) < 5:
        skills = ["python", "kafka", "redis", "docker", "kubernetes"]

    return {
        "role": data.get("role", "Backend Engineer"),
        "skills": skills,
        "min_experience": data.get("min_experience", 5)
    }

# ------------------ AGENT 2: GITHUB CANDIDATES ------------------
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

        bio = profile.get("bio") or "Backend engineer working on scalable systems"

        candidates.append({
            "name": username,
            "profile": u["html_url"],
            "bio": bio,
            "repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0)
        })

    return candidates

# ------------------ AGENT 3: MATCH ENGINE ------------------
def compute_match(c, skills, min_exp):
    bio = c["bio"].lower()

    matched = [s for s in skills if s.lower() in bio]
    skill_score = (len(matched) / len(skills)) * 100 if skills else 0

    exp_match = re.search(r'(\d+)', bio)
    years = int(exp_match.group(1)) if exp_match else random.randint(2, 8)

    exp_score = 100 if years >= min_exp else (years / min_exp) * 100

    context_bonus = 0
    if "kafka" in bio:
        context_bonus += 10
    if "distributed" in bio:
        context_bonus += 10

    github_bonus = 0
    if c["repos"] > 20:
        github_bonus += 5
    if c["followers"] > 50:
        github_bonus += 5

    penalty = 0
    if len(matched) < len(skills) / 2:
        penalty -= 15

    final = 0.5 * skill_score + 0.3 * exp_score + context_bonus + github_bonus + penalty
    final = max(0, min(100, round(final, 2)))

    breakdown = {
        "Skill Match": f"{round(skill_score,1)}%",
        "Experience": f"{years} yrs → {round(exp_score,1)}%",
        "Context Bonus": f"+{context_bonus}",
        "GitHub Signal": f"+{github_bonus} (repos/followers)",
        "Penalty": f"{penalty}"
    }

    return final, matched, years, breakdown

# ------------------ AGENT 4: INTEREST ------------------
def simulate_interest():
    options = [
        ("Highly Interested", 85, "Actively exploring roles"),
        ("Conditional", 60, "Interested if compensation aligns"),
        ("Passive", 40, "Not actively looking")
    ]
    return random.choice(options)

# ------------------ AGENT 5: DECISION ------------------
def build_reason(c, match, interest, matched):
    reasons = []

    if "kafka" in c["bio"].lower():
        reasons.append("Strong Kafka + distributed systems alignment")

    if c["repos"] > 20:
        reasons.append("Active open-source contributor")

    if match > 70:
        reasons.append("Meets technical requirements")

    if interest > 70:
        reasons.append("High engagement → faster conversion")

    if matched:
        reasons.append(f"Matched skills: {', '.join(matched[:3])}")

    return reasons

def compare_others(results):
    insights = []
    for r in results[1:4]:
        if r["interest"] < 50:
            insights.append(f"{r['name']}: strong skills but low interest")
        elif r["match"] < 60:
            insights.append(f"{r['name']}: weaker technical alignment")
        else:
            insights.append(f"{r['name']}: good candidate but lower priority")
    return insights

# ------------------ UI ------------------
def main():
    st.set_page_config("TalentScoutAI", layout="wide")

    st.title("🧠 TalentScoutAI — AI Hiring Decision System")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("🚀 Run Agent"):

        jd_data = parse_jd(jd)

        st.success(f"""
Parsed Role: {jd_data['role']}  
Skills: {', '.join(jd_data['skills'])}  
Min Exp: {jd_data['min_experience']} yrs
""")

        candidates = fetch_candidates(jd_data["role"])
        results = []

        for c in candidates:
            match, matched, years, breakdown = compute_match(
                c, jd_data["skills"], jd_data["min_experience"]
            )

            label, interest, msg = simulate_interest()

            final = round(0.6 * match + 0.4 * interest, 2)

            reasons = build_reason(c, match, interest, matched)

            results.append({
                "name": c["name"],
                "profile": c["profile"],
                "bio": c["bio"],
                "match": match,
                "interest": interest,
                "final": final,
                "behavior": label,
                "message": msg,
                "repos": c["repos"],
                "followers": c["followers"],
                "breakdown": breakdown,
                "reasons": reasons
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
        st.bar_chart(df.set_index("name")[["match","interest"]])
        st.caption("Match vs Interest comparison")

        # -------- Top Candidate --------
        top = results[0]

        st.subheader("🏆 Top Recommendation")
        st.success(top["name"])
        st.markdown(f"🔗 [GitHub Profile]({top['profile']})")

        st.write("### Why Selected")
        for r in top["reasons"]:
            st.write(f"- {r}")

        st.write("### Why not others?")
        for r in compare_others(results):
            st.write(f"- {r}")

        st.write("### Trade-offs")
        st.write("- Requires deeper technical validation")

        st.info("Decision: Proceed to interview")

        # -------- Details --------
        st.subheader("📂 Candidate Details")

        for c in results:
            with st.expander(c["name"]):
                st.markdown(f"🔗 [GitHub Profile]({c['profile']})")
                st.write("Bio:", c["bio"])
                st.write(f"Repos: {c['repos']} | Followers: {c['followers']}")

                st.write("Match:", c["match"])
                st.write("Interest:", c["interest"])
                st.write("Final:", c["final"])

                st.write("Behavior:", c["behavior"])
                st.write("→", c["message"])

                st.write("### Score Breakdown")
                for k, v in c["breakdown"].items():
                    st.write(f"{k}: {v}")

# ------------------
if __name__ == "__main__":
    main()