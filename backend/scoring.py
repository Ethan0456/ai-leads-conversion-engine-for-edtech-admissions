"""
Scoring engine: profile scoring, conversation scoring, priority calculation.
"""
from datetime import datetime

# ---------------------------------------------------------------------------
# PROGRAMS (hardcoded)
# ---------------------------------------------------------------------------
PROGRAMS = [
    {
        "name": "Data Science",
        "skills": ["python", "statistics", "ml", "machine learning", "data", "sql", "pandas", "numpy"],
        "description": "Master data analysis, ML pipelines, and business intelligence.",
    },
    {
        "name": "Full Stack Development",
        "skills": ["javascript", "react", "node", "html", "css", "web", "frontend", "backend", "fullstack", "full stack"],
        "description": "Build end-to-end web apps with modern JS frameworks.",
    },
    {
        "name": "AI/ML Engineering",
        "skills": ["ai", "ml", "deep learning", "nlp", "pytorch", "tensorflow", "llm", "openai"],
        "description": "Deep-dive into AI systems, LLMs, and production ML.",
    },
]

# ---------------------------------------------------------------------------
# PROFILE SCORING
# ---------------------------------------------------------------------------

def compute_fit_score(skills: list[str], experience: str) -> float:
    """Score 0-100 based on skills relevance to our programs."""
    skill_lower = [s.lower() for s in skills]
    matched = 0
    all_keywords = []
    for p in PROGRAMS:
        all_keywords.extend(p["skills"])
    for kw in all_keywords:
        if any(kw in s for s in skill_lower):
            matched += 1
    # Normalise: cap at 10 keyword matches = 100
    fit = min(matched / max(len(all_keywords), 1) * 200, 100)

    # Bonus for experience
    exp_lower = experience.lower()
    for word in ["3", "4", "5", "6", "7", "8", "9", "10"]:
        if word in exp_lower:
            fit = min(fit + 15, 100)
            break
    return round(fit, 2)


def compute_intent_score(candidate: dict) -> float:
    """Score 0-100 based on profile completeness."""
    fields = [
        candidate.get("name"),
        candidate.get("email"),
        candidate.get("education"),
        candidate.get("experience"),
        candidate.get("skills"),
        candidate.get("program_interest"),
    ]
    filled = sum(1 for f in fields if f)
    score = (filled / len(fields)) * 100
    # Bonus for certifications
    if candidate.get("certifications"):
        score = min(score + 10, 100)
    return round(score, 2)


def compute_profile_score(fit: float, intent: float) -> float:
    return round(0.6 * fit + 0.4 * intent, 2)


# ---------------------------------------------------------------------------
# CONVERSATION SCORING
# ---------------------------------------------------------------------------

CONVERSATION_RULES = {
    "replied": 10,
    "multiple_replies": 10,
    "asked_question": 20,
    "asked_pricing": 25,
    "asked_duration_outcomes": 20,
    "agreed_to_schedule": 30,
}

PRICING_KEYWORDS = ["price", "cost", "fee", "fees", "tuition", "how much", "payment", "afford"]
DURATION_KEYWORDS = ["duration", "long", "weeks", "months", "outcome", "salary", "job", "placement", "guarantee"]
SCHEDULE_KEYWORDS = ["schedule", "book", "call", "meeting", "appointment", "yes", "interested", "sign up", "enroll"]
QUESTION_KEYWORDS = ["?", "what", "how", "when", "where", "why", "which", "can i", "do you", "is there"]


def score_message(text: str, reply_count: int, current_score: float) -> tuple[float, list[str]]:
    """
    Evaluate a single user message and return (new_score, triggered_rules).
    """
    t = text.lower()
    triggered = []
    delta = 0

    # +10 replied
    delta += CONVERSATION_RULES["replied"]
    triggered.append("replied")

    # +10 multiple replies
    if reply_count > 1:
        delta += CONVERSATION_RULES["multiple_replies"]
        triggered.append("multiple_replies")

    # +20 asked question
    if any(kw in t for kw in QUESTION_KEYWORDS):
        delta += CONVERSATION_RULES["asked_question"]
        triggered.append("asked_question")

    # +25 pricing
    if any(kw in t for kw in PRICING_KEYWORDS):
        delta += CONVERSATION_RULES["asked_pricing"]
        triggered.append("asked_pricing")

    # +20 duration/outcomes
    if any(kw in t for kw in DURATION_KEYWORDS):
        delta += CONVERSATION_RULES["asked_duration_outcomes"]
        triggered.append("asked_duration_outcomes")

    # +30 agreed to schedule
    if any(kw in t for kw in SCHEDULE_KEYWORDS):
        delta += CONVERSATION_RULES["agreed_to_schedule"]
        triggered.append("agreed_to_schedule")

    new_score = min(current_score + delta, 100)
    return round(new_score, 2), triggered


# ---------------------------------------------------------------------------
# INTERACTION LEVEL
# ---------------------------------------------------------------------------

def compute_interaction_level(reply_count: int, conversation_score: float, status: str) -> float:
    if status == "scheduled":
        return 1.0
    if reply_count == 0:
        return 0.0
    if reply_count == 1:
        return 0.3
    if conversation_score >= 80:
        return 0.9
    if conversation_score >= 60:
        return 0.7
    if reply_count >= 2:
        return 0.5
    return 0.3


# ---------------------------------------------------------------------------
# PRIORITY SCORE
# ---------------------------------------------------------------------------

def compute_priority_score(interaction_level: float, profile_score: float, conversation_score: float) -> float:
    score = (1 - interaction_level) * profile_score + interaction_level * conversation_score
    return round(score, 2)


# ---------------------------------------------------------------------------
# PROGRAM MATCHING
# ---------------------------------------------------------------------------

def match_programs(candidate: dict) -> list[dict]:
    skill_lower = [s.lower() for s in candidate.get("skills", [])]
    interest = candidate.get("program_interest", "").lower()

    scored = []
    for prog in PROGRAMS:
        match_count = sum(1 for kw in prog["skills"] if any(kw in s for s in skill_lower) or kw in interest)
        scored.append((match_count, prog))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]

    result = []
    for count, prog in top:
        reason = f"Matched {count} skill/interest signals." if count > 0 else "General fit based on profile."
        result.append({"name": prog["name"], "description": prog["description"], "reason": reason})
    return result


# ---------------------------------------------------------------------------
# SCHEDULING SLOTS
# ---------------------------------------------------------------------------

def get_schedule_slots(priority_score: float) -> list[str]:
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    if priority_score >= 80:
        days = [0, 1]
    elif priority_score >= 60:
        days = [2, 3]
    elif priority_score >= 40:
        days = [3, 4, 5]
    else:
        days = [5, 7, 10]

    slots = []
    for d in days:
        dt = now + timedelta(days=d)
        slots.append(dt.strftime("%A, %d %b %Y at 10:00 AM UTC"))
        slots.append(dt.strftime("%A, %d %b %Y at 3:00 PM UTC"))
    return slots[:4]


# ---------------------------------------------------------------------------
# DECAY
# ---------------------------------------------------------------------------

def apply_decay(conversation_score: float) -> float:
    return round(conversation_score * 0.9, 2)
