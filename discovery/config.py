"""
Configuration for job discovery pipeline.
Search parameters, scoring weights, keywords, and thresholds.
"""

# ---------------------------------------------------------------------------
# Search queries to run against each source
# ---------------------------------------------------------------------------

SEARCH_QUERIES = [
    "operations manager",
    "business operations",
    "automation consultant",
    "data migration",
    "business analyst",
    "project manager operations",
    "process improvement",
]

# Location
LOCATION = "Atlanta, GA"
REMOTE_PREFERRED = True

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "role_type": 0.30,
    "skills": 0.20,
    "work_arrangement": 0.20,
    "company_size": 0.10,
    "industry": 0.10,
    "seniority": 0.10,
}

# Minimum score to write to Notion
MIN_SCORE_THRESHOLD = 3.0

# Maximum age of listings to fetch (hours)
MAX_LISTING_AGE_HOURS = 48

# Stale threshold (days)
STALE_THRESHOLD_DAYS = 30

# Fallback trigger: if fewer than this many new jobs from APIs, run JobSpy
JOBSPY_FALLBACK_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Role type keywords (for 30% scoring dimension)
# ---------------------------------------------------------------------------

ROLE_KEYWORDS = {
    "operations": [
        "operations", "ops manager", "business ops", "operations manager",
        "operations analyst", "operations lead", "operations coordinator",
        "operations director", "operations specialist",
    ],
    "automation": [
        "automation", "process automation", "rpa", "workflow automation",
        "automation engineer", "automation consultant", "automation specialist",
    ],
    "data_migration": [
        "data migration", "data conversion", "data integration",
        "etl", "platform migration", "system migration",
    ],
    "business_analysis": [
        "business analyst", "business analysis", "requirements analyst",
        "process improvement", "process optimization", "business intelligence",
    ],
    "project_management": [
        "project manager", "program manager", "project lead",
        "program management", "pmo", "project coordinator",
    ],
}

# ---------------------------------------------------------------------------
# Will's skills (from resume)
# ---------------------------------------------------------------------------

SKILLS = [
    "process improvement", "compliance operations", "robotic process automation",
    "rpa", "risk reduction", "cost-benefit analysis", "training program development",
    "change management", "user adoption", "data governance", "requirements gathering",
    "ai for business operations", "responsible ai", "machine learning",
    "stakeholder management", "cross-departmental coordination",
    "team development", "business analysis", "data migration",
    "operations consulting", "automation", "project management",
    "feasibility assessment", "performance metrics", "program design",
]

# ---------------------------------------------------------------------------
# Work arrangement classification
# ---------------------------------------------------------------------------

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "telecommute", "fully remote"]
HYBRID_KEYWORDS = ["hybrid", "flexible", "partially remote"]
ONSITE_KEYWORDS = [
    "on-site", "onsite", "in-office", "in office",
    "must be in office", "on-site required", "not remote",
]

ATLANTA_KEYWORDS = [
    "atlanta", "atl", "georgia", " ga ", ",ga", ", ga",
    "alpharetta", "marietta", "decatur", "sandy springs",
    "roswell", "kennesaw", "duluth", "lawrenceville",
    "johns creek", "brookhaven", "dunwoody",
]

# ---------------------------------------------------------------------------
# Industry classification
# ---------------------------------------------------------------------------

INDUSTRY_RISK_MGMT = [
    "risk management", "risk consulting", "enterprise risk",
    "operational risk", "risk analytics", "grc",
    "governance risk compliance",
]
INDUSTRY_FINSERV = [
    "financial services", "fintech", "insurtech", "banking",
    "capital markets", "wealth management", "payments",
    "lending", "credit", "financial technology",
]
INDUSTRY_INSURANCE = [
    "insurance carrier", "insurance company", "underwriting company",
    "claims processing", "policy administration",
]

# ---------------------------------------------------------------------------
# Seniority keywords
# ---------------------------------------------------------------------------

SENIORITY_MID_SENIOR = [
    "manager", "senior", "lead", "sr.", "sr ", "principal",
    "team lead", "supervisor",
]
SENIORITY_DIRECTOR = [
    "director", "head of", "vp", "vice president",
]
SENIORITY_ENTRY = [
    "entry-level", "entry level", "junior", "jr.",
    "associate", "coordinator", "0-2 years",
    "recent graduate", "no experience required",
]
SENIORITY_EXECUTIVE = [
    "c-suite", "chief", "ceo", "cfo", "coo", "cto", "cio",
    "executive vice president", "evp", "svp",
]

# ---------------------------------------------------------------------------
# Dealbreaker detection
# ---------------------------------------------------------------------------

DEALBREAKER_TRAVEL = [
    r"travel\s+required",
    r"\d+%\s+travel",
    r"travel\s+up\s+to",
    r"frequent\s+travel",
    r"overnight\s+travel",
    r"extensive\s+travel",
]

DEALBREAKER_ONSITE_STRICT = [
    r"on[\-\s]site\s+(required|only|mandatory)",
    r"must\s+be\s+in\s+office",
    r"in[\-\s]office\s+only",
    r"not\s+remote",
    r"no\s+remote",
]

DEALBREAKER_TOXIC = [
    r"wear\s+many\s+hats",
    r"like\s+a\s+family",
    r"must\s+be\s+available\s+24",
]

# ---------------------------------------------------------------------------
# Red flag patterns (non-dealbreaker but worth noting)
# ---------------------------------------------------------------------------

RED_FLAG_PATTERNS = {
    "overqualification_risk": [
        r"entry[\-\s]level", r"junior", r"0[\-\s]2\s+years",
        r"recent\s+graduate", r"no\s+experience\s+required",
    ],
    "underqualification_risk": [
        r"c[\-\s]suite", r"vp\s+of", r"vice\s+president",
        r"chief\s+.*officer", r"15\+?\s+years", r"20\+?\s+years",
    ],
    "high_pressure_signals": [
        r"fast[\-\s]paced.*unlimited\s+pto",
        r"high[\-\s]pressure",
    ],
}

# ---------------------------------------------------------------------------
# Company size mapping
# ---------------------------------------------------------------------------

COMPANY_SIZE_SMALL = ["1-50", "1-10", "11-50", "small", "startup"]
COMPANY_SIZE_MEDIUM = ["51-200", "51-250", "201-500", "medium", "mid-size", "midsize"]
COMPANY_SIZE_LARGE = ["501-1000", "1001-5000", "5001-10000", "10001+", "large", "enterprise"]
