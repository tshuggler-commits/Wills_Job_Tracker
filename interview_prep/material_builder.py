"""
Interview prep material assembly.

Gathers job description, company research, behavioral questions,
and interview strategy into structured documents for NotebookLM and email.
"""

import sys
import os
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

# Add parent directory for config imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from discovery import config


# ---------------------------------------------------------------------------
# User-Agent (matches link_checker.py)
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# PrepMaterials dataclass
# ---------------------------------------------------------------------------

@dataclass
class PrepMaterials:
    """All assembled prep materials for one job."""
    job_description_text: str
    company_research_text: str
    behavioral_questions_text: str
    interview_tips_text: str
    full_document: str          # All sections combined
    scrape_succeeded: bool


# ---------------------------------------------------------------------------
# Will's profile (for STAR hints and competitive advantages)
# ---------------------------------------------------------------------------

WILL_PROFILE = {
    "name": "Will Sharp",
    "experience_years": "10+",
    "employers": ["Hiscox USA", "AIG"],
    "military": "U.S. Marine Corps veteran",
    "education": "BBA in Risk Management and Insurance, Georgia State University",
    "designation": "AINS (Associate in Insurance)",
    "certifications": "AI certifications (2023-present)",
    "core_strengths": [
        "Operations management and process improvement",
        "Robotic process automation (RPA) implementation",
        "Cross-departmental coordination and stakeholder management",
        "Change management and user adoption",
        "Data governance and migration",
        "Compliance operations",
        "Training program development",
    ],
    "competitive_advantages": [
        ("Military background", "Discipline, leadership under pressure, mission-focused execution"),
        ("Insurance operations expertise", "Deep domain knowledge across carriers (Hiscox, AIG)"),
        ("AI certifications", "Forward-thinking, technology adoption mindset"),
        ("AINS designation", "Professional credibility in risk and insurance"),
        ("Process automation track record", "Quantifiable improvements from RPA and workflow automation"),
        ("Veteran status", "Protected class, many employers actively recruit veterans"),
    ],
}


# ---------------------------------------------------------------------------
# Behavioral question bank
# ---------------------------------------------------------------------------

QUESTION_BANK = {
    "operations": [
        {
            "q": "Tell me about a time you identified and eliminated an operational inefficiency.",
            "hint": "Hiscox RPA implementation — automated manual processing steps, reduced turnaround time.",
        },
        {
            "q": "Describe a situation where you had to manage competing operational priorities.",
            "hint": "AIG/Hiscox — balancing compliance deadlines with process improvement initiatives.",
        },
        {
            "q": "How have you measured the success of operational improvements you've led?",
            "hint": "Metrics: processing time reduction, error rate decrease, cost savings, user adoption rates.",
        },
        {
            "q": "Tell me about a process you built from scratch.",
            "hint": "Training programs, onboarding workflows, or automation pipelines at Hiscox.",
        },
    ],
    "process_improvement": [
        {
            "q": "Walk me through how you approach identifying processes that need improvement.",
            "hint": "Data-driven: map current state, measure bottlenecks, prioritize by impact and feasibility.",
        },
        {
            "q": "Describe a time when a process change you championed faced resistance. How did you handle it?",
            "hint": "Change management at a carrier — stakeholder buy-in, training, phased rollout.",
        },
        {
            "q": "Tell me about a cost-benefit analysis you conducted for a process change.",
            "hint": "RPA ROI analysis — implementation cost vs. hours saved, error reduction.",
        },
    ],
    "stakeholder_management": [
        {
            "q": "How do you build relationships with stakeholders across different departments?",
            "hint": "Cross-departmental coordination at AIG/Hiscox — regular check-ins, shared goals, transparency.",
        },
        {
            "q": "Describe a time you had to influence a decision without having direct authority.",
            "hint": "Marine Corps → corporate translation: leading through influence, data-backed proposals.",
        },
        {
            "q": "Tell me about a time you had to deliver difficult news to a stakeholder.",
            "hint": "Project delays, scope changes — frame the problem, present options, recommend a path.",
        },
    ],
    "change_management": [
        {
            "q": "How have you driven adoption of new tools or systems?",
            "hint": "Training programs, documentation, phased rollouts, feedback loops.",
        },
        {
            "q": "Tell me about a time you led a team through a significant organizational change.",
            "hint": "System migrations, RPA adoption — communication plan, training, support structure.",
        },
        {
            "q": "How do you handle pushback when implementing new processes?",
            "hint": "Listen first, address concerns with data, pilot programs, celebrate early wins.",
        },
    ],
    "data_migration": [
        {
            "q": "Walk me through a data migration project you've managed.",
            "hint": "Planning, data mapping, validation rules, testing, cutover strategy, rollback plan.",
        },
        {
            "q": "How do you ensure data quality during a migration?",
            "hint": "Validation rules, reconciliation reports, spot checks, stakeholder sign-off.",
        },
        {
            "q": "What's the most challenging aspect of data migration and how do you handle it?",
            "hint": "Legacy system complexity, incomplete documentation — discovery phase, domain expert interviews.",
        },
    ],
    "problem_solving": [
        {
            "q": "Tell me about a time you solved a problem that others couldn't figure out.",
            "hint": "Root cause analysis, cross-referencing data, looking beyond the obvious symptoms.",
        },
        {
            "q": "Describe a situation where you had to make a decision with incomplete information.",
            "hint": "Military training → corporate application: assess risk, act decisively, adjust course.",
        },
        {
            "q": "How do you approach a problem you've never encountered before?",
            "hint": "Research, break into components, consult experts, prototype solutions, iterate.",
        },
    ],
    "leadership": [
        {
            "q": "Tell me about your leadership style.",
            "hint": "Marine Corps foundation: mission-first, lead by example, develop your team, clear communication.",
        },
        {
            "q": "Describe a time you mentored or developed someone on your team.",
            "hint": "Training program development at Hiscox — structured learning, hands-on coaching.",
        },
        {
            "q": "How do you handle underperformance on your team?",
            "hint": "Direct conversation, understand root cause, set clear expectations, support plan, follow up.",
        },
    ],
    "remote_work": [
        {
            "q": "How do you stay productive and engaged in a remote work environment?",
            "hint": "Structured schedule, proactive communication, documentation-first culture.",
        },
        {
            "q": "How do you build team cohesion when working remotely?",
            "hint": "Regular 1:1s, async standups, virtual team activities, over-communicate in writing.",
        },
        {
            "q": "How do you handle communication challenges in a distributed team?",
            "hint": "Time zone awareness, async-first, clear written communication, video for complex topics.",
        },
    ],
    "automation": [
        {
            "q": "Tell me about an automation project you've led from concept to deployment.",
            "hint": "RPA at Hiscox — identified opportunity, built business case, implemented, measured results.",
        },
        {
            "q": "How do you decide which processes are good candidates for automation?",
            "hint": "High volume, rule-based, repetitive, error-prone, measurable ROI.",
        },
        {
            "q": "What's your approach to evaluating automation tools and technologies?",
            "hint": "Requirements gathering, vendor comparison, proof of concept, total cost of ownership.",
        },
    ],
    "project_management": [
        {
            "q": "How do you manage project scope and prevent scope creep?",
            "hint": "Clear requirements doc, change request process, stakeholder alignment, regular check-ins.",
        },
        {
            "q": "Tell me about a project that didn't go as planned and how you recovered.",
            "hint": "Acknowledge early, communicate transparently, re-plan, focus on what you can control.",
        },
        {
            "q": "How do you prioritize when everything feels urgent?",
            "hint": "Impact vs. effort matrix, stakeholder alignment on priorities, timeboxing.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Job description scraper
# ---------------------------------------------------------------------------

def scrape_job_description(apply_link):
    """
    Scrape job description text from an Apply Link URL.
    Returns (text, success_bool).
    """
    if not apply_link:
        return "", False

    try:
        resp = requests.get(
            apply_link,
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code != 200:
            return "", False

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove scripts, styles, nav elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Try to find main content area
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"job|description|content|posting", re.I))
            or soup.find("div", id=re.compile(r"job|description|content|posting", re.I))
        )

        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Truncate if too long (NotebookLM limit is 500K words but keep it reasonable)
        if len(text) > 15000:
            text = text[:15000] + "\n\n[Truncated — full description at apply link]"

        if len(text) < 100:
            return "", False

        return text, True

    except Exception:
        return "", False


# ---------------------------------------------------------------------------
# Source document builders
# ---------------------------------------------------------------------------

def _build_job_description_doc(job, scraped_text, scrape_succeeded):
    """Build Source 1: Job Description document."""
    lines = [
        f"# Job Description: {job['title']} at {job['company']}",
        "",
        "## Position Details",
        f"- Title: {job['title']}",
        f"- Company: {job['company']}",
    ]
    if job.get("work_type"):
        lines.append(f"- Work Type: {job['work_type']}")
    if job.get("employment_type"):
        lines.append(f"- Employment Type: {job['employment_type']}")
    if job.get("salary_range"):
        lines.append(f"- Salary Range: {job['salary_range']}")

    lines.append("")

    if scrape_succeeded and scraped_text:
        lines.append("## Full Description")
        lines.append(scraped_text)
    else:
        lines.append("## Description Summary (from tracker)")
        if job.get("company_intel"):
            lines.append(job["company_intel"])
        else:
            lines.append(f"Position: {job['title']} at {job['company']}")

    if job.get("apply_link"):
        lines.append("")
        lines.append(f"## Apply Link")
        lines.append(job["apply_link"])

    return "\n".join(lines)


def _build_company_research_doc(job):
    """Build Source 2: Company Research Brief."""
    lines = [
        f"# Company Research: {job['company']}",
        "",
        "## Overview",
        f"- Company: {job['company']}",
    ]

    if job.get("company_size"):
        lines.append(f"- Size: {job['company_size']}")
    if job.get("industry"):
        lines.append(f"- Industry: {job['industry']}")
    if job.get("company_rating"):
        lines.append(f"- Company Rating: {job['company_rating']}/5")
    if job.get("work_type"):
        lines.append(f"- Work Type: {job['work_type']}")

    if job.get("company_intel"):
        lines.append("")
        lines.append("## Company Intelligence")
        lines.append(job["company_intel"])

    red_flags = job.get("red_flags", "")
    if red_flags:
        lines.append("")
        lines.append("## Red Flags to Be Aware Of")
        lines.append(red_flags)
        lines.append("")
        lines.append("Consider probing these areas during the interview:")
        lines.append("- Ask about team culture and management style")
        lines.append("- Ask about work-life balance and typical hours")
        lines.append("- Ask about turnover rate and tenure on the team")
    else:
        lines.append("")
        lines.append("## Red Flags")
        lines.append("None identified from initial screening.")

    lines.append("")
    lines.append("## Questions to Ask About the Company")
    lines.append("- What is the team structure and who would I report to?")
    lines.append("- What does success look like in the first 90 days?")
    lines.append("- What tools and technologies does the team currently use?")
    lines.append("- How does the company approach professional development?")

    if job.get("industry"):
        lines.append(f"- How does the company approach {job['industry']}-specific challenges?")

    return "\n".join(lines)


def _select_questions(job, scraped_text):
    """Select the most relevant behavioral questions based on job content."""
    # Combine all available text for keyword matching
    text = " ".join([
        job.get("title", ""),
        job.get("company_intel", ""),
        scraped_text or "",
    ]).lower()

    # Score each category by keyword relevance
    category_scores = {}

    keyword_map = {
        "operations": config.ROLE_KEYWORDS.get("operations", []),
        "process_improvement": config.ROLE_KEYWORDS.get("business_analysis", []) + ["process improvement", "optimization"],
        "automation": config.ROLE_KEYWORDS.get("automation", []),
        "data_migration": config.ROLE_KEYWORDS.get("data_migration", []),
        "project_management": config.ROLE_KEYWORDS.get("project_management", []),
        "stakeholder_management": ["stakeholder", "cross-functional", "cross-departmental", "collaborate"],
        "change_management": ["change management", "adoption", "transformation", "transition"],
        "leadership": ["lead", "manager", "director", "team", "supervise", "mentor"],
        "problem_solving": ["problem", "troubleshoot", "analyze", "diagnose", "resolve"],
        "remote_work": ["remote", "distributed", "virtual", "work from home"],
    }

    for category, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            category_scores[category] = score

    # Always include leadership and problem_solving (universal)
    category_scores.setdefault("leadership", 1)
    category_scores.setdefault("problem_solving", 1)

    # Sort by score, take top categories
    sorted_categories = sorted(category_scores.items(), key=lambda x: -x[1])
    selected = []

    for category, _score in sorted_categories:
        if category in QUESTION_BANK:
            selected.extend(QUESTION_BANK[category])
        if len(selected) >= 15:
            break

    # Cap at 15 questions
    return selected[:15]


def _build_behavioral_questions_doc(job, scraped_text):
    """Build Source 3: Behavioral Interview Questions."""
    questions = _select_questions(job, scraped_text)

    lines = [
        f"# Behavioral Interview Questions: {job['title']} at {job['company']}",
        "",
        "## About the Candidate (Will Sharp)",
        f"- {WILL_PROFILE['experience_years']} years operations experience at {', '.join(WILL_PROFILE['employers'])}",
        f"- {WILL_PROFILE['military']}",
        f"- {WILL_PROFILE['education']}",
        f"- {WILL_PROFILE['designation']}",
        f"- {WILL_PROFILE['certifications']}",
        "",
        "## Tailored Questions",
        "",
    ]

    for i, q in enumerate(questions, 1):
        lines.append(f"### Question {i}")
        lines.append(f'"{q["q"]}"')
        lines.append("")
        lines.append(f"**STAR Hint:** {q['hint']}")
        lines.append("")

    return "\n".join(lines)


def _build_interview_tips_doc(job):
    """Build Source 4: Interview Strategy Guide."""
    lines = [
        f"# Interview Strategy: {job['title']} at {job['company']}",
        "",
        "## Your Competitive Advantages",
        "",
    ]

    for i, (advantage, detail) in enumerate(WILL_PROFILE["competitive_advantages"], 1):
        lines.append(f"{i}. **{advantage}** — {detail}")

    lines.append("")
    lines.append("## Key Talking Points for This Role")
    lines.append("")

    # Dynamic talking points based on role type
    title_lower = job.get("title", "").lower()
    intel_lower = job.get("company_intel", "").lower()
    combined = f"{title_lower} {intel_lower}"

    if any(kw in combined for kw in ["operations", "ops"]):
        lines.append("- Emphasize your track record of operational improvements with measurable outcomes")
        lines.append("- Reference specific metrics: processing time reductions, error rate decreases, cost savings")
    if any(kw in combined for kw in ["automation", "rpa"]):
        lines.append("- Lead with your RPA implementation experience — concrete examples of automation ROI")
        lines.append("- Mention your AI certifications to show you're staying current with automation trends")
    if any(kw in combined for kw in ["project", "program"]):
        lines.append("- Highlight your ability to manage complex, multi-stakeholder projects")
        lines.append("- Share examples of scope management, timeline adherence, and risk mitigation")
    if any(kw in combined for kw in ["data", "migration", "analytics"]):
        lines.append("- Discuss your data migration methodology: planning, validation, testing, cutover")
        lines.append("- Emphasize data quality and governance experience")
    if any(kw in combined for kw in ["risk", "compliance"]):
        lines.append("- Your AINS designation and insurance operations background are directly relevant")
        lines.append("- Discuss how you've balanced compliance requirements with operational efficiency")

    # Default talking points
    lines.append("- Connect your military experience to discipline, leadership, and mission execution")
    lines.append("- Position your AI certifications as evidence of continuous learning and adaptability")

    # Questions to ask
    lines.append("")
    lines.append("## Questions YOU Should Ask")
    lines.append("")
    lines.append("- What does a typical day look like in this role?")
    lines.append("- What are the biggest challenges the team is facing right now?")
    lines.append("- How do you measure success in this position?")
    lines.append("- What opportunities for growth exist in this role?")
    lines.append("- Can you tell me about the team I'd be working with?")

    # Company size-specific questions
    company_size = (job.get("company_size") or "").lower()
    if company_size in ["small", "startup"]:
        lines.append("- How is the company funded and what's the runway?")
        lines.append("- How many people are on the team today? Growth plans?")
    elif company_size in ["large", "enterprise"]:
        lines.append("- How does this role interact with other departments?")
        lines.append("- What's the decision-making process for new initiatives?")

    # Red flag probing
    red_flags = job.get("red_flags", "")
    if red_flags:
        lines.append("")
        lines.append("## Red Flag Probing Questions")
        lines.append(f"Red flags identified: {red_flags}")
        lines.append("- Ask about work-life balance expectations directly")
        lines.append("- Ask what happened with the previous person in this role")
        lines.append("- Ask about typical working hours and on-call expectations")

    # Remote-specific tips
    work_type = job.get("work_type", "")
    if work_type in ["Remote", "Hybrid"]:
        lines.append("")
        lines.append("## Remote Interview Tips")
        lines.append("- Test your camera, microphone, and internet before the call")
        lines.append("- Choose a clean, well-lit background")
        lines.append("- Have a glass of water and your notes nearby (out of camera view)")
        lines.append("- Make eye contact by looking at the camera, not the screen")
        lines.append("- Ask about the team's communication tools and async culture")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_prep_materials(job):
    """
    Assemble all prep materials for one job.
    job: dict from extract_job() in notion_common.py
    Returns: PrepMaterials
    """
    # Scrape job description
    scraped_text, scrape_succeeded = scrape_job_description(job.get("apply_link", ""))

    # Build each source document
    job_desc = _build_job_description_doc(job, scraped_text, scrape_succeeded)
    company_research = _build_company_research_doc(job)
    behavioral_qs = _build_behavioral_questions_doc(job, scraped_text)
    interview_tips = _build_interview_tips_doc(job)

    # Combine into single document
    full_document = "\n\n---\n\n".join([
        job_desc,
        company_research,
        behavioral_qs,
        interview_tips,
    ])

    return PrepMaterials(
        job_description_text=job_desc,
        company_research_text=company_research,
        behavioral_questions_text=behavioral_qs,
        interview_tips_text=interview_tips,
        full_document=full_document,
        scrape_succeeded=scrape_succeeded,
    )
