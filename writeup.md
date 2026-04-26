How the Project Works

The agent automates the technical recruiter’s workflow from JD to shortlist. A user pastes a job description (and optionally a location) into a Streamlit interface. The system then executes five steps:
1.	JD Parsing – A Groq LLM (llama-3.1-8b-instant) extracts the role, required skills, and minimum years of experience. Output is forced to valid JSON.
2.	Candidate Discovery – The GitHub API searches for users matching the role (plus location filter if provided). For each candidate, the bio, public repos, followers, and location are fetched. The Stack Exchange API then adds reputation score and top tags.
3.	Match Score Calculation – A hybrid scoring engine uses:
o	Semantic similarity (Sentence BERT) – cosine between candidate bio and required skills.
o	Keyword matching – explicit skill mentions in bio.
o	Experience parsing – regex extraction of years (e.g., “5+ years”) compared to JD’s minimum.
o	Stack Overflow bonus – +15 (rep >2000), +8 (500 2000), +3 (100 500).
Final match = 0.5×semantic + 0.25×keyword + 0.25×experience + bonus.
4.	Outreach Simulation – For the top 6 matched candidates:
o	Icebreaker – Fetches the candidate’s last GitHub commit message, then asks Groq to write a friendly one sentence opener referencing that commit.
o	Two turn chat – Groq role plays the candidate (attitude depends on match score). First recruiter message includes the icebreaker. Second asks for a 15 min call.
o	Interest Score – A RoBERTa sentiment model (cardiffnlp/twitter-roberta-base-sentiment) analyses the candidate’s second reply. Positive → 80 100, neutral → 50, negative → 10 30.
5.	Ranking & Presentation – Final score = 60% Match + 40% Interest. UI shows bar chart, metric cards, top recommendation with trade offs, expandable candidate cards (breakdown + conversation), and a downloadable CSV.

Unique Selling Points (USP)

USP	Why It Matters
Real world candidate data	Uses live GitHub + Stack Overflow APIs – no fake profiles. Recruiters see actual developers with real bios, repos, and community reputation.
Personalised icebreaker from commit history	The agent reads the candidate’s latest commit message and generates a unique opening line. This mimics a human recruiter who has done research, increasing reply rates.
Hybrid matching with explainability	Combines semantic meaning, keyword presence, experience parsing, and SO reputation. Every score component is shown, so recruiters trust the ranking.
Sentiment based interest scoring	Instead of naive “yes/no”, it uses a fine tuned social media sentiment model. Detects enthusiasm (“love to!”) vs. hesitation (“maybe…”), giving a nuanced interest metric.
Location aware or global search	User can type any city/country to focus locally, or leave empty for worldwide search. No hard coded geographies.
One click deployable	Works locally with a .env file or on Streamlit Cloud with a single secret. No complicated infrastructure.


Key Performance Indicators (KPIs)
KPI	Target / Observed Value	How Measured
JD parsing accuracy	>95% correct extraction of role, skills, min experience	Manual check on 10 diverse JDs
Candidate discovery relevance	≥80% of returned GitHub users have bio related to the role	Sample inspection
Match score differentiation	Scores span >40 points across candidates (no identical scores)	Standard deviation of match scores >15
Icebreaker personalisation rate	100% of top 6 candidates receive a commit based icebreaker (fallback generic only if API fails)	Code logs / UI preview
Interest score correlation	Positive replies yield score >70, negative <40 – verified with 20 test conversations	Manual validation
End to end latency	<30 seconds for 6 candidates (including all API calls)	time measurements
Recruiter actionability	Shortlist includes clear “why selected” and “trade offs” – recruiter can proceed without extra research	Qualitative evaluation

Trade offs Made
•	GitHub rate limits – Unauthenticated: 60 requests/hour. Mitigation: caching (@st.cache_data) and optional GITHUB_TOKEN.
•	Conversation simulation – Not live email/LinkedIn (requires OAuth). Saves development time while still demonstrating the icebreaker + sentiment logic.
•	Sentiment model on CPU – Adds ~1 second per candidate but avoids external API cost. Acceptable for ≤6 candidates.

Conclusion
The agent transforms a manual, hours long recruitment screening into an automated, repeatable pipeline. It delivers a recruiter grade shortlist in under 30 seconds, combining real data, transparent scoring, and realistic engagement simulation – ready for production as a recruitment copilot.

