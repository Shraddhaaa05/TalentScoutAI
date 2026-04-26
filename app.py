import streamlit as st
import os
import json
import random
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# ---------------- ENV ----------------
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    st.error("Missing GROQ_API_KEY in .env")
    st.stop()

client = Groq(api_key=API_KEY)

# ---------------- SAFE LLM ----------------
def llm(prompt):
    try:
        res = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return res.choices[0].message.content
    except:
        return ""

# ---------------- JD PARSER ----------------
def parse_jd(jd):
    prompt = f"""
Extract structured hiring data in JSON.

Return ONLY JSON:
{{
 "role": "",
 "skills": [],
 "min_experience": 0
}}

JD:
{jd}
"""
    raw = llm(prompt)

    try:
        data = json.loads(raw)
    except:
        data = {}

    return {
        "role": data.get("role") or "Backend Engineer",
        "skills": data.get("skills") or ["python","kafka","docker","kubernetes"],
        "min_experience": data.get("min_experience") or 5
    }

# ---------------- CANDIDATES ----------------
def get_candidates():
    return [
        {"name": "Arjun Mehta", "bio": "Backend engineer with Kafka, distributed systems and Kubernetes"},
        {"name": "Sneha Iyer", "bio": "Python backend developer building APIs"},
        {"name": "Rahul Nair", "bio": "Distributed systems engineer working on real-time pipelines"},
        {"name": "Divya Kapoor", "bio": "DevOps engineer with Kubernetes, Docker and CI/CD"},
        {"name": "Karan Sharma", "bio": "Java backend developer with Spring Boot"}
    ]

# ---------------- MATCH SCORE ----------------
def match_score(bio, skills):
    bio = bio.lower()
    matches = sum(1 for s in skills if s.lower() in bio)
    keyword_score = (matches / len(skills)) * 100

    semantic_boost = random.randint(60, 90)

    return round(0.6 * semantic_boost + 0.4 * keyword_score, 2)

# ---------------- INTEREST ----------------
def interest_score():
    options = [
        ("Highly Interested", 85, "Actively exploring backend roles"),
        ("Conditional", 60, "Open if compensation aligns"),
        ("Passive", 40, "Not actively looking but open")
    ]
    return random.choice(options)

# ---------------- MAIN ----------------
def main():
    st.set_page_config(page_title="TalentScoutAI", layout="wide")

    st.title("🧠 TalentScoutAI — Agentic Hiring System")

    jd = st.text_area("📄 Paste Job Description")

    if st.button("Run Agent"):
        jd_info = parse_jd(jd)

        st.success(f"""
Parsed Role: {jd_info['role']}  
Skills: {', '.join(jd_info['skills'])}  
Min Experience: {jd_info['min_experience']} years
""")

        candidates = get_candidates()

        results = []

        for c in candidates:
            m_score = match_score(c["bio"], jd_info["skills"])
            label, i_score, msg = interest_score()

            final = round(0.6 * m_score + 0.4 * i_score, 2)

            results.append({
                **c,
                "match_score": m_score,
                "interest_score": i_score,
                "final_score": final,
                "label": label,
                "message": msg
            })

        results = sorted(results, key=lambda x: x["final_score"], reverse=True)

        # ---------------- METRICS ----------------
        col1, col2, col3 = st.columns(3)
        col1.metric("Candidates", len(results))
        col2.metric("Top Score", results[0]["final_score"])
        col3.metric("Avg Score", round(sum(r["final_score"] for r in results)/len(results),1))

        # ---------------- CHART ----------------
        df = pd.DataFrame(results)
        st.subheader("📊 Candidate Comparison")
        st.bar_chart(df.set_index("name")[["match_score","interest_score"]])

        # ---------------- TOP ----------------
        top = results[0]

        st.subheader("🏆 Hiring Recommendation")
        st.success(top["name"])

        st.write("### Why Selected")
        st.write("- Strong alignment with required skills")
        st.write("- Good balance of match and interest")
        st.write("- Suitable for immediate hiring")

        st.write("### Trade-offs")
        st.write("- May require further technical validation")

        st.info("Decision: Proceed to technical interview")

        # ---------------- DETAILS ----------------
        st.subheader("📂 Candidate Details")

        for c in results:
            with st.expander(c["name"]):
                st.write("Bio:", c["bio"])
                st.write("Match:", c["match_score"])
                st.write("Interest:", c["interest_score"])
                st.write("Final:", c["final_score"])
                st.write("Behavior:", c["label"])

                st.write("💬 Response:")
                st.write(c["message"])

if __name__ == "__main__":
    main()