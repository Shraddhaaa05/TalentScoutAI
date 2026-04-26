import streamlit as st
import pandas as pd
import re
import json
import os
import random
from groq import Groq
from dotenv import load_dotenv

# ------------------ SETUP ------------------
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

if not GROQ_KEY:
    st.error("Missing GROQ_API_KEY")
    st.stop()

client = Groq(api_key=GROQ_KEY)

MODEL = "llama3-8b-8192"

# ------------------ AGENT 1: JD PARSER ------------------
def parse_jd(jd):
    prompt = f"""
Extract ALL technical skills, tools, and concepts.

Also extract:
- role
- min_experience

Return JSON ONLY.

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

# ------------------ CANDIDATES ------------------
def get_candidates():
    return [
        {"name": "Arjun Mehta", "bio": "Backend engineer with 6 years experience building Kafka pipelines, Kubernetes deployments and distributed systems"},
        {"name": "Sneha Iyer", "bio": "Python developer with 4 years experience building APIs and dashboards"},
        {"name": "Rahul Nair", "bio": "Distributed systems engineer with 8 years experience, strong in Kafka and large-scale systems"},
        {"name": "Divya Kapoor", "bio": "DevOps engineer with Kubernetes, Docker, CI/CD and cloud infrastructure, 5 years experience"},
        {"name": "Karan Sharma", "bio": "Java backend developer with APIs and microservices, 7 years experience"}
    ]

# ------------------ MATCH ENGINE ------------------
def compute_match(candidate, skills, min_exp):
    bio = candidate["bio"].lower()

    matched = [s for s in skills if s.lower() in bio]
    skill_score = (len(matched) / len(skills)) * 100

    exp_match = re.search(r'(\d+)', bio)
    years = int(exp_match.group(1)) if exp_match else 0

    exp_score = 100 if years >= min_exp else (years / min_exp) * 100

    context_bonus = 0
    if "distributed" in bio:
        context_bonus += 10
    if "kafka" in bio:
        context_bonus += 10

    penalty = 0
    if years > min_exp + 5:
        penalty -= 10
    if len(matched) < len(skills) / 2:
        penalty -= 15

    final = 0.5 * skill_score + 0.3 * exp_score + context_bonus + penalty
    final = max(0, min(100, round(final, 2)))

    breakdown = {
        "Skill Match": f"{round(skill_score,1)}%",
        "Experience": f"{years} yrs (score {round(exp_score,1)}%)",
        "Context Bonus": f"+{context_bonus}",
        "Penalty": f"{penalty}"
    }

    return final, matched, years, breakdown

# ------------------ INTEREST ------------------
def simulate_interest():
    options = [
        ("Highly Interested", 85, "Actively exploring roles"),
        ("Conditional", 60, "Interested if compensation aligns"),
        ("Passive", 40, "Not actively looking")
    ]
    return random.choice(options)

# ------------------ REASONING ------------------
def build_reason(candidate, match, interest, matched):
    reasons = []

    if "kafka" in candidate["bio"].lower():
        reasons.append("Strong Kafka + distributed systems alignment")

    if match > 70:
        reasons.append("Meets core technical requirements")

    if interest > 70:
        reasons.append("High engagement → faster conversion")

    return reasons

def compare_others(results):
    reasons = []
    for r in results[1:4]:
        if r["interest"] < 50:
            reasons.append(f"{r['name']}: strong skills but low interest")
        elif r["match"] < 60:
            reasons.append(f"{r['name']}: weaker technical alignment")
        else:
            reasons.append(f"{r['name']}: decent fit but not top choice")
    return reasons

# ------------------ UI ------------------
def main():
    st.set_page_config(page_title="TalentScoutAI", layout="wide")

    st.title("🧠 TalentScoutAI — Decision Intelligence Hiring Agent")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("Run Agent"):

        jd_data = parse_jd(jd)

        st.success(f"""
Parsed Role: {jd_data['role']}  
Skills: {', '.join(jd_data['skills'])}  
Min Exp: {jd_data['min_experience']} yrs
""")

        candidates = get_candidates()
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
                "bio": c["bio"],
                "match": match,
                "interest": interest,
                "final": final,
                "behavior": label,
                "message": msg,
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

        st.write("### Why Selected")
        for r in top["reasons"]:
            st.write(f"- {r}")

        st.write("### Trade-offs")
        st.write("- Requires deeper technical validation")

        st.write("### Why not others?")
        for r in compare_others(results):
            st.write(f"- {r}")

        st.info("Decision: Proceed to interview")

        # -------- Details --------
        st.subheader("📂 Candidate Details")

        for c in results:
            with st.expander(c["name"]):
                st.write("Bio:", c["bio"])
                st.write("Match Score:", c["match"])
                st.write("Interest Score:", c["interest"])
                st.write("Final Score:", c["final"])

                st.write("Behavior:", c["behavior"])
                st.write("→", c["message"])

                st.write("### Score Breakdown")
                for k, v in c["breakdown"].items():
                    st.write(f"{k}: {v}")

# ------------------
if __name__ == "__main__":
    main()