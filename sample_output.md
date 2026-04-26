# 🎯 Sample Input / Output – TalentScoutAI

## 📥 Input Job Description

```text
Senior Backend Engineer – Distributed Systems
TechCorp | Remote | Full-time

Requirements:
- 5+ years of backend engineering experience
- Strong Python or Go
- Apache Kafka, Redis, PostgreSQL
- Kubernetes and Docker
- Distributed systems concepts
```

---

## 🧠 Parsed Job Description

```json
{
  "role": "Senior Backend Engineer",
  "skills": ["Python", "Go", "Kafka", "Redis", "PostgreSQL", "Kubernetes", "Docker"],
  "min_experience": 5
}
```

---

## 📊 Candidate Ranking

| Rank | Name           | Match Score | Interest | Final Score |
|------|----------------|------------|----------|------------|
| 1    | Arjun Mehta    | 78.4       | 85       | 81.0       |
| 2    | Rahul Nair     | 72.1       | 60       | 67.2       |
| 3    | Sneha Iyer     | 61.3       | 70       | 65.0       |

---

## 🏆 Top Recommendation

**Arjun Mehta**

### Why Selected:
- Strong Kafka + distributed systems experience  
- Matches backend + scaling requirements  
- High likelihood of interest  

### Trade-offs:
- Slightly higher notice period  

### Decision:
→ Proceed to technical interview  

---

## 📂 Candidate Details

### 👤 Arjun Mehta
- Bio: Backend engineer with Kafka, Kubernetes, distributed systems  
- Match Score: 78.4  
- Interest: Highly Interested  

**Conversation:**
```
Recruiter: Your Kafka experience stood out — we’re solving similar scale problems.

Candidate: That sounds interesting, I’d like to know more.
```

---

### 👤 Rahul Nair
- Bio: Distributed systems engineer with data pipeline experience  
- Match Score: 72.1  
- Interest: Conditional  

---

### 👤 Sneha Iyer
- Bio: Python backend developer building APIs  
- Match Score: 61.3  
- Interest: Moderate  

---

## 📈 Score Logic

Final Score =  
**0.6 × Match Score + 0.4 × Interest Score**

---

## 💡 Key Insight

This system does not just rank candidates —  
it simulates **real hiring decisions with trade-offs and uncertainty**.
