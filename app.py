import streamlit as st
import os
import json
import random
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# ------------------ Load API ------------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("API key not found. Please set GROQ_API_KEY in .env")
    st.stop()

client = Groq(api_key=api_key)

# ------------------ LLM helper ------------------
def call_llm(prompt):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return ""

# ------------------ JD Parsing ------------------
def parse_jd(jd_text):
    prompt = f"""
Extract role, skills and experience from this job description.
Return ONLY JSON in this format:
{{
 "role": "",
 "skills": [],
 "min_experience": 0
}}

JD:
{jd_text}
"""
    result = call_llm(prompt)

    try:
        data = json.loads(result)
    except:
        data = {}

    return {
        "role": data.get("role", "Backend Engineer"),
        "skills": data.get("skills", ["python", "api", "docker"]),
        "min_experience": data.get("min_experience", 3)
    }

# ------------------ Dummy candidates ------------------
def get_candidates():
    return [
        {"name": "Arjun", "bio": "Backend engineer working with Python, Kafka and Docker"},
        {"name": "Sneha", "bio": "Python developer building APIs and dashboards"},
        {"name": "Rahul", "bio": "Distributed systems engineer with Kubernetes experience"},
        {"name": "Divya", "bio": "DevOps engineer handling CI/CD and cloud deployments"},
        {"name": "Karan", "bio": "Software engineer with Java and backend services"}
    ]

# ------------------ Scoring ------------------
def calculate_match_score(bio, skills):
    bio = bio.lower()
    matches = sum(1 for s in skills if s.lower() in bio)
    score = (matches / len(skills)) * 100
    noise = random.randint(5, 20)
    return round(min(score + noise, 100), 2)

def simulate_interest():
    options = [
        ("High", 80),
        ("Medium", 60),
        ("Low", 40)
    ]
    return random.choice(options)

# ------------------ UI ------------------
def main():
    st.title("TalentScoutAI")

    jd_input = st.text_area("Paste Job Description")

    if st.button("Run Analysis"):

        jd_data = parse_jd(jd_input)

        st.success(f"""
Role: {jd_data['role']}
Skills: {", ".join(jd_data['skills'])}
Min Experience: {jd_data['min_experience']} years
""")

        candidates = get_candidates()

        results = []

        for c in candidates:
            match = calculate_match_score(c["bio"], jd_data["skills"])
            label, interest = simulate_interest()

            final_score = round(0.6 * match + 0.4 * interest, 2)

            results.append({
                "name": c["name"],
                "match": match,
                "interest": interest,
                "final": final_score,
                "behavior": label,
                "bio": c["bio"]
            })

        results = sorted(results, key=lambda x: x["final"], reverse=True)

        df = pd.DataFrame(results)

        st.subheader("Candidate Scores")
        st.dataframe(df)

        st.subheader("Top Candidate")
        top = results[0]

        st.write(f"Name: {top['name']}")
        st.write(f"Final Score: {top['final']}")
        st.write("Reason: Good alignment with required skills and reasonable interest level")

# ------------------
if __name__ == "__main__":
    main()