import streamlit as st
import requests
import pandas as pd
import json
import os
import re
import random
from dotenv import load_dotenv
from groq import Groq

# ---------------- CONFIG ----------------
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN")

if not GROQ_KEY:
    st.error("Missing GROQ API Key")
    st.stop()

client = Groq(api_key=GROQ_KEY)
MODEL = "llama3-8b-8192"

# ---------------- LOAD SKILLS ----------------
with open("skills.json") as f:
    SKILLS_DB = json.load(f)

# ---------------- DOMAIN DETECTION ----------------
def detect_domain(jd):
    jd = jd.lower()

    if any(x in jd for x in ["machine learning","ai","nlp","data","software","engineer"]):
        return "tech"
    if any(x in jd for x in ["marketing","seo","campaign"]):
        return "marketing"
    if any(x in jd for x in ["finance","accounting","audit"]):
        return "finance"
    if any(x in jd for x in ["legal","law","compliance"]):
        return "legal"
    if any(x in jd for x in ["hr","recruitment","talent"]):
        return "hr"

    return "general"

# ---------------- JD VALIDATION ----------------
def is_valid_jd(jd):
    return len(jd.strip()) > 80

# ---------------- PARSER ----------------
def parse_jd(jd):
    if not is_valid_jd(jd):
        st.error("Invalid JD")
        st.stop()

    domain = detect_domain(jd)
    jd_lower = jd.lower()

    skills_pool = SKILLS_DB.get(domain, [])
    skills = [s for s in skills_pool if s in jd_lower]

    # inference
    if domain == "tech":
        if "nlp" in jd_lower:
            skills.append("nlp")

    exp_match = re.search(r'(\d+)', jd_lower)
    min_exp = int(exp_match.group(1)) if exp_match else 0

    return {
        "domain": domain,
        "role": domain.capitalize(),
        "skills": list(set(skills)),
        "min_exp": min_exp
    }

# ---------------- GITHUB (TECH ONLY) ----------------
def fetch_github_candidates(role):
    url = f"https://api.github.com/search/users?q={role}&per_page=5"
    headers = {}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    users = requests.get(url, headers=headers).json().get("items", [])

    candidates = []

    for u in users:
        profile = requests.get(f"https://api.github.com/users/{u['login']}", headers=headers).json()

        candidates.append({
            "name": u["login"],
            "profile": u["html_url"],
            "bio": profile.get("bio") or "Software engineer",
            "repos": profile.get("public_repos", 0)
        })

    return candidates

# ---------------- NON-TECH CANDIDATES ----------------
def generate_candidates(domain):
    templates = {
        "marketing": "Digital marketer with SEO and campaign experience",
        "finance": "Financial analyst with reporting and valuation skills",
        "legal": "Legal researcher with compliance and contract expertise",
        "hr": "HR professional with recruitment experience",
        "general": "Professional with relevant domain experience"
    }

    return [
        {"name": f"Candidate_{i}", "bio": templates.get(domain)}
        for i in range(5)
    ]

# ---------------- MATCH ----------------
def compute_match(bio, skills):
    bio = bio.lower()
    matched = [s for s in skills if s in bio]

    score = (len(matched) / len(skills)) * 100 if skills else 50
    return round(score, 2), matched

def build_reasoning(candidate, skills, match, interest, matched):
    reasons = []
    risks = []

    # Skill reasoning
    if matched:
        reasons.append(f"Matches {len(matched)}/{len(skills)} required skills ({', '.join(matched[:3])})")
    else:
        risks.append("No strong skill alignment")

    # Match strength
    if match > 75:
        reasons.append("Strong technical fit")
    elif match > 50:
        reasons.append("Moderate alignment")
    else:
        risks.append("Weak technical fit")

    # Interest reasoning
    if interest > 75:
        reasons.append("High engagement → faster conversion")
    elif interest < 50:
        risks.append("Low candidate interest")

    # Final insight
    decision = "Proceed to interview"
    if risks:
        decision = "Proceed with caution"

    return reasons, risks, decision

# ---------------- UI ----------------
def main():
    st.set_page_config(page_title="TalentScoutAI", layout="wide")

    st.title("🧠 TalentScoutAI — Hiring Decision Dashboard")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("🚀 Run Agent"):

        parsed = parse_jd(jd)

        st.success(f"""
**Domain:** {parsed['domain']}  
**Skills:** {', '.join(parsed['skills'])}  
**Experience:** {parsed['min_exp']} yrs
""")

        # -------- Candidate Source --------
        if parsed["domain"] == "tech":
            candidates = fetch_github_candidates(parsed["role"])
        else:
            candidates = generate_candidates(parsed["domain"])

        results = []

        for c in candidates:
            match, matched = compute_match(c["bio"], parsed["skills"])
            interest = random.randint(40, 90)

            final = round(0.6 * match + 0.4 * interest, 2)

            reasons, risks, decision = build_reasoning(
                c, parsed["skills"], match, interest, matched
            )

            results.append({
                "name": c["name"],
                "bio": c["bio"],
                "profile": c.get("profile", ""),
                "match": match,
                "interest": interest,
                "final": final,
                "reasons": reasons,
                "risks": risks,
                "decision": decision
            })

        results = sorted(results, key=lambda x: x["final"], reverse=True)

        # -------- KPI CARDS --------
        col1, col2, col3 = st.columns(3)
        col1.metric("Candidates", len(results))
        col2.metric("Top Score", results[0]["final"])
        col3.metric("Avg Score", round(sum(r["final"] for r in results)/len(results),1))

        # -------- CHART --------
        df = pd.DataFrame(results)
        st.subheader("📊 Candidate Comparison")
        st.bar_chart(df.set_index("name")[["match", "interest"]])

        # -------- TOP CANDIDATE --------
        top = results[0]

        st.subheader("🏆 Top Recommendation")

        with st.container():
            st.markdown(f"### {top['name']}")
            if top["profile"]:
                st.markdown(f"[🔗 View Profile]({top['profile']})")

            st.markdown("#### ✅ Why Selected")
            for r in top["reasons"]:
                st.write(f"- {r}")

            if top["risks"]:
                st.markdown("#### ⚠️ Risks")
                for r in top["risks"]:
                    st.write(f"- {r}")

            st.success(f"Decision: {top['decision']}")

        # -------- COMPARISON --------
        st.subheader("⚖️ Why not others")

        for r in results[1:4]:
            st.write(f"**{r['name']}** → Lower score due to:")
            if r["risks"]:
                for risk in r["risks"]:
                    st.write(f"- {risk}")
            else:
                st.write("- Slightly weaker overall profile")

        # -------- FULL DETAILS --------
        st.subheader("📂 Candidate Profiles")

        for c in results:
            with st.expander(c["name"]):
                st.write("Bio:", c["bio"])

                if c["profile"]:
                    st.markdown(f"[GitHub/Profile Link]({c['profile']})")

                st.write(f"Match Score: {c['match']}")
                st.write(f"Interest Score: {c['interest']}")
                st.write(f"Final Score: {c['final']}")

                st.markdown("**Why Selected**")
                for r in c["reasons"]:
                    st.write(f"- {r}")

                if c["risks"]:
                    st.markdown("**Risks**")
                    for r in c["risks"]:
                        st.write(f"- {r}")
# ---------------- RUN ----------------
if __name__ == "__main__":
    main()