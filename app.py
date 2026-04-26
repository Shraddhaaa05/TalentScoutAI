import streamlit as st
import requests
import pandas as pd
import re
import json
import os
from sentence_transformers import SentenceTransformer, util
from groq import Groq
from transformers import pipeline
from dotenv import load_dotenv
import time

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_MODEL = "llama-3.1-8b-instant"

if not GROQ_KEY:
    st.error("❌ GROQ_API_KEY missing. Set it in .env or Streamlit secrets.")
    st.stop()

# ---------- JD parser ----------
def parse_job_description(jd_text):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"""
Extract from job description. Return ONLY valid JSON.
Keys: role, skills (list), min_experience (int).
Example: {{"role": "Backend Engineer", "skills": ["python","kafka"], "min_experience": 5}}
JD:
{jd_text}
"""
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        if not data.get("role"): data["role"] = "Backend Engineer"
        if not data.get("skills"): data["skills"] = ["python", "docker"]
        if not data.get("min_experience"): data["min_experience"] = 3
        return data
    except Exception as e:
        st.error(f"JD parsing failed: {e}")
        st.stop()

# ---------- GitHub + Stack Overflow ----------
@st.cache_data(ttl=3600)
def fetch_github_candidates(role, location=None, limit=10):
    query = f"{role}" + (f" location:{location}" if location and location.strip() else "")
    url = f"https://api.github.com/search/users?q={query}&per_page={limit}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        users = resp.json().get("items", [])
        candidates = []
        for user in users:
            u = requests.get(user["url"], headers=headers, timeout=5).json()
            candidates.append({
                "name": u.get("name") or user["login"],
                "username": user["login"],
                "profile_url": user["html_url"],
                "bio": u.get("bio") or "",
                "public_repos": u.get("public_repos", 0),
                "followers": u.get("followers", 0),
                "location": u.get("location") or "",
            })
        return candidates
    except:
        return []

def enrich_stackoverflow(candidate):
    try:
        url = f"https://api.stackexchange.com/2.3/users?inname={candidate['username']}&site=stackoverflow"
        resp = requests.get(url, timeout=5).json()
        if resp.get("items"):
            so = resp["items"][0]
            candidate["so_reputation"] = so.get("reputation", 0)
            candidate["so_tags"] = [t["name"] for t in so.get("tags", [])][:3]
        else:
            candidate["so_reputation"] = 0
            candidate["so_tags"] = []
    except:
        candidate["so_reputation"] = 0
        candidate["so_tags"] = []
    return candidate

# ---------- Matching engine ----------
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

def match_candidates(candidates, required_skills, min_exp):
    model = load_model()
    skill_emb = model.encode(required_skills, convert_to_tensor=True)
    scored = []
    for c in candidates:
        bio = c["bio"].lower()
        yexp = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', bio, re.I)
        exp_years = int(yexp.group(1)) if yexp else 0
        
        bio_emb = model.encode(bio, convert_to_tensor=True)
        semantic = float(util.cos_sim(bio_emb, skill_emb)[0].mean()) * 100
        
        matched = [s for s in required_skills if s.lower() in bio]
        keyword = (len(matched)/len(required_skills))*100 if required_skills else 0
        
        exp_score = 100 if exp_years >= min_exp else (exp_years/min_exp)*100 if min_exp>0 else 0
        
        rep = c.get("so_reputation", 0)
        bonus = 15 if rep>2000 else (8 if rep>500 else (3 if rep>100 else 0))
        
        match = 0.5*semantic + 0.25*keyword + 0.25*exp_score + bonus
        match = min(100, round(match, 2))
        
        c["match_score"] = match
        c["exp_years"] = exp_years
        c["matched_skills"] = matched
        c["explanation"] = {
            "Semantic": f"{semantic:.1f}%",
            "Keywords": f"{keyword:.1f}% – {', '.join(matched[:3])}" if matched else "none",
            "Experience": f"{exp_score:.1f}% – {exp_years} yrs vs {min_exp}",
            "SO Bonus": f"+{bonus}"
        }
        scored.append(c)
    return sorted(scored, key=lambda x: x["match_score"], reverse=True)

# ---------- Sentiment & conversation ----------
sentiment_pipeline = None
def get_sentiment():
    global sentiment_pipeline
    if sentiment_pipeline is None:
        sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment", device=-1)
    return sentiment_pipeline

def interest_from_reply(text):
    if not text or len(text)<5:
        return 50
    try:
        res = get_sentiment()(text[:512])[0]
        if res['label'] == 'positive':
            return min(100, int(res['score']*100))
        elif res['label'] == 'negative':
            return max(0, 30 - int(res['score']*30))
        return 50
    except:
        return 50

def icebreaker_from_github(username):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        url = f"https://api.github.com/users/{username}/events/public"
        events = requests.get(url, headers=headers, timeout=5).json()
        commits = [e for e in events if e['type'] == 'PushEvent']
        if commits:
            last_msg = commits[0]['payload']['commits'][0]['message']
            client = Groq(api_key=GROQ_KEY)
            prompt = f"Write a friendly 1‑sentence icebreaker for a recruiter. Mention this commit: '{last_msg[:60]}'. Keep natural, ≤25 words."
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            return resp.choices[0].message.content.strip()
        else:
            return f"Hi {username}, saw your GitHub – cool work!"
    except:
        return f"Hey {username}, your open source activity caught my eye."

def simulate_conversation(cand, role, skills):
    ice = icebreaker_from_github(cand['username'])
    skills_str = ', '.join(skills[:3])
    client = Groq(api_key=GROQ_KEY)
    
    msg1 = f"{ice} We're hiring {role} – need {skills_str}. Open for a quick chat?"
    attitude = "very enthusiastic" if cand['match_score'] > 75 else "cautiously interested"
    prompt1 = f"You are {cand['name']} (real dev). Bio: '{cand['bio']}'. Attitude: {attitude}. Reply (1 sentence) to: '{msg1}'"
    r1 = client.chat.completions.create(model=GROQ_MODEL, messages=[{"role":"user","content":prompt1}], temperature=0.7)
    reply1 = r1.choices[0].message.content
    
    msg2 = f"Great! Could you spare 15 min this week for a call about {role}?"
    prompt2 = f"Continue as {cand['name']}. Reply realistically (interested/not sure/busy). To: '{msg2}'"
    r2 = client.chat.completions.create(model=GROQ_MODEL, messages=[{"role":"user","content":prompt2}], temperature=0.7)
    reply2 = r2.choices[0].message.content
    
    interest = interest_from_reply(reply2)
    return [{"role":"Recruiter","msg":msg1}, {"role":cand['name'],"msg":reply1}, {"role":"Recruiter","msg":msg2}, {"role":cand['name'],"msg":reply2}], interest

# ---------- UI ----------
def main():
    st.set_page_config("Catalyst Scout", layout="wide")
    st.markdown("<h1 style='text-align:center;'>🧠 Agentic AI Talent Scouting & Engagement</h1>", unsafe_allow_html=True)
    st.caption("Real GitHub · Semantic Matching · Sentiment Interest · Personalized Icebreakers")
    
    with st.sidebar:
        st.header("📍 Location (optional)")
        location = st.text_input("City / Country", placeholder="e.g., India, Bangalore, leave empty for global")
    
    jd = st.text_area("📄 Paste Job Description", height=200)
    
    if st.button("🚀 Run Agent", type="primary", use_container_width=True):
        if not jd.strip():
            st.error("Paste a job description.")
            return
        
        with st.spinner("Parsing JD..."):
            info = parse_job_description(jd)
        st.success(f"**Parsed:** {info['role']} | Skills: {', '.join(info['skills'])} | Min Exp: {info['min_experience']} yrs")
        
        with st.spinner(f"Searching GitHub{' in ' + location if location else ' globally'}..."):
            raw = fetch_github_candidates(info['role'], location)
        if not raw:
            st.error("No candidates found. Check GitHub rate limit or token.")
            return
        st.info(f"Found {len(raw)} profiles")
        
        with st.spinner("Enriching with Stack Overflow..."):
            enriched = [enrich_stackoverflow(c) for c in raw]
        
        with st.spinner("Computing match scores..."):
            matched = match_candidates(enriched, info['skills'], info['min_experience'])
        
        top6 = matched[:6]
        with st.spinner("Simulating conversations (~15 sec)..."):
            prog = st.progress(0)
            for i, c in enumerate(top6):
                conv, interest = simulate_conversation(c, info['role'], info['skills'])
                c['conversation'] = conv
                c['interest_score'] = interest
                prog.progress((i+1)/len(top6))
            prog.empty()
        
        for c in top6:
            c['final_score'] = 0.6*c['match_score'] + 0.4*c.get('interest_score',50)
        final = sorted(top6, key=lambda x: x['final_score'], reverse=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📊 Total", len(matched))
        col2.metric("🏆 Top Match", f"{final[0]['match_score']:.1f}")
        avg_int = sum(c.get('interest_score',50) for c in final)/len(final)
        col3.metric("💡 Avg Interest", f"{avg_int:.1f}")
        
        # bar chart
        df_chart = pd.DataFrame([{"user":c['username'], "Match":c['match_score'], "Interest":c.get('interest_score',50)} for c in final])
        st.subheader("📊 Candidate Comparison")
        st.bar_chart(df_chart.set_index("user"))
        
        # top recommendation
        top = final[0]
        st.subheader("🏆 Top Recommendation")
        with st.container():
            st.markdown(f"### {top['name']} (@{top['username']})")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**✅ Why selected**")
                st.write(f"- Match Score: {top['match_score']}")
                st.write(f"- Interest: {top.get('interest_score',50)}")
                st.write(f"- Experience: {top['exp_years']} years")
                if top.get('matched_skills'):
                    st.write(f"- Skills in bio: {', '.join(top['matched_skills'][:3])}")
            with col_b:
                st.markdown("**⚠️ Trade‑offs**")
                if top.get('so_reputation',0) < 500:
                    st.write("- Lower SO reputation")
                if top['public_repos'] < 10:
                    st.write("- Few public repos")
                st.write("- Needs technical interview validation")
            st.info("💼 **Decision:** Proceed to technical screen")
        
        # expandable details
        st.subheader("📂 Shortlist Details")
        for idx, c in enumerate(final):
            with st.expander(f"{idx+1}. {c['name']} | Match: {c['match_score']} | Interest: {c.get('interest_score',50)}"):
                st.write(f"**GitHub:** [{c['username']}]({c['profile_url']})")
                st.write(f"**Bio:** {c['bio']}")
                st.write(f"**Location:** {c.get('location','?')}")
                if c.get('so_reputation'):
                    st.write(f"**SO Rep:** {c['so_reputation']} – tags: {', '.join(c.get('so_tags',[]))}")
                st.write("**Match breakdown:**")
                for k,v in c['explanation'].items():
                    st.write(f"  - {k}: {v}")
                st.write("**💬 Conversation:**")
                for turn in c.get('conversation', []):
                    st.write(f"*{turn['role']}:* {turn['msg']}")
        
        # CSV
        export = pd.DataFrame([{
            "Name": c['name'],
            "Match": c['match_score'],
            "Interest": c.get('interest_score','N/A'),
            "Final": c.get('final_score','N/A'),
            "GitHub": c['profile_url'],
            "Location": c.get('location','')
        } for c in matched])
        st.download_button("📥 Download CSV (all)", export.to_csv(index=False), "shortlist.csv", use_container_width=True)

if __name__ == "__main__":
    main()