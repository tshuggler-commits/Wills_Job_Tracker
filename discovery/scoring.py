"""
Job scoring engine.
Scores each RawJob 0-10 against Will's profile with transparent explanations.
"""

import re
from dataclasses import dataclass, field
from .sources.base import RawJob
from .location_filter import has_us_signal
from . import config

# Penalty applied to work arrangement score when location is ambiguous
UNCONFIRMED_LOCATION_PENALTY = 0.5


@dataclass
class ScoredJob:
    """A job with its match score and metadata."""
    raw: RawJob
    score: float
    score_breakdown: dict
    explanation: str
    red_flags: list
    is_dealbreaker: bool
    work_type: str       # "Remote", "Hybrid", "On-site"
    employment_type: str  # "Full-time", "Part-time", "Contract"
    priority: str        # "High", "Medium", "Low"


def _text_lower(job):
    """Combine title + description + location for searching."""
    return f"{job.title} {job.description} {job.location}".lower()


def _title_lower(job):
    return job.title.lower()


def _check_patterns(text, patterns):
    """Check if any regex pattern matches the text."""
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _detect_dealbreakers(job):
    """Check for dealbreaker conditions. Returns list of reasons or empty list."""
    text = _text_lower(job)
    title = _title_lower(job)
    reasons = []

    # Travel required
    for p in config.DEALBREAKER_TRAVEL:
        if re.search(p, text, re.IGNORECASE):
            match = re.search(p, text, re.IGNORECASE)
            reasons.append(f"Travel required ({match.group()})")
            break

    # On-site required outside Atlanta
    is_onsite_strict = False
    for p in config.DEALBREAKER_ONSITE_STRICT:
        if re.search(p, text, re.IGNORECASE):
            is_onsite_strict = True
            break

    if is_onsite_strict:
        # Check if it's in Atlanta metro
        is_atlanta = any(kw in text for kw in config.ATLANTA_KEYWORDS)
        if not is_atlanta:
            reasons.append("On-site required outside Atlanta metro")

    # Toxic signals: flag if 2+ toxic patterns match
    toxic_matches = []
    for p in config.DEALBREAKER_TOXIC:
        if re.search(p, text, re.IGNORECASE):
            toxic_matches.append(re.search(p, text, re.IGNORECASE).group())
    if len(toxic_matches) >= 2:
        reasons.append(f"Toxic signals ({', '.join(toxic_matches)})")

    return reasons


def _detect_red_flags(job):
    """Check for non-dealbreaker red flags."""
    text = _text_lower(job)
    flags = []

    for flag_name, patterns in config.RED_FLAG_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                label = flag_name.replace("_", " ").title()
                flags.append(label)
                break

    return flags


def _score_role_type(job):
    """Score 0-3.0 based on role type keyword matching."""
    title = _title_lower(job)
    text = _text_lower(job)
    max_score = 3.0

    title_matches = []
    desc_matches = []

    for category, keywords in config.ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                title_matches.append(category)
                break
            elif kw in text:
                desc_matches.append(category)
                break

    if title_matches:
        # Title match = 2.0 base, bonus for multiple categories
        score = min(2.0 + (len(title_matches) - 1) * 0.5, max_score)
        matched = title_matches
    elif desc_matches:
        # Description-only match = 1.0 base
        score = min(1.0 + (len(desc_matches) - 1) * 0.3, 2.0)
        matched = desc_matches
    else:
        return 0.0, "No role type match"

    categories = list(set(title_matches + desc_matches))
    return score, f"Role: {', '.join(categories)} ({score:.1f}/{max_score})"


def _score_skills(job):
    """Score 0-2.0 based on skills overlap."""
    text = _text_lower(job)
    max_score = 2.0

    matches = [s for s in config.SKILLS if s in text]
    if not matches:
        return 0.0, "No skills match"

    ratio = len(matches) / len(config.SKILLS)
    score = min(ratio * max_score * 2, max_score)  # Scale up since partial match is expected

    top_matches = matches[:5]
    return score, f"Skills: {', '.join(top_matches)} ({score:.1f}/{max_score})"


def _classify_work_arrangement(job):
    """Classify as Remote/Hybrid/On-site and return score 0-2.0.

    Applies a penalty when location has no confirmed US signal.
    """
    text = _text_lower(job)
    max_score = 2.0
    location = job.location or ""
    confirmed_us = has_us_signal(location)

    # Check for explicit "not remote" / "no remote" before checking for "remote"
    has_anti_remote = any(kw in text for kw in config.ONSITE_KEYWORDS)

    if not has_anti_remote and (job.is_remote or any(kw in text for kw in config.REMOTE_KEYWORDS)):
        if confirmed_us:
            return "Remote", max_score, f"Remote ({max_score}/{max_score})"
        score = max(max_score - UNCONFIRMED_LOCATION_PENALTY, 0)
        return "Remote", score, f"Remote, unconfirmed US ({score}/{max_score})"

    if any(kw in text for kw in config.HYBRID_KEYWORDS):
        is_atlanta = any(kw in text for kw in config.ATLANTA_KEYWORDS)
        if is_atlanta:
            return "Hybrid", 1.5, f"Hybrid ATL (1.5/{max_score})"
        if confirmed_us:
            return "Hybrid", 1.0, f"Hybrid non-ATL (1.0/{max_score})"
        score = max(1.0 - UNCONFIRMED_LOCATION_PENALTY, 0)
        return "Hybrid", score, f"Hybrid, unconfirmed US ({score}/{max_score})"

    is_atlanta = any(kw in text for kw in config.ATLANTA_KEYWORDS)
    if is_atlanta:
        return "On-site", 0.5, f"On-site ATL (0.5/{max_score})"

    return "On-site", 0.0, f"On-site non-ATL (0.0/{max_score})"


def _score_company_size(job):
    """Score 0-1.0 based on company size preference."""
    max_score = 1.0
    size = (job.company_size or "").lower()

    if not size:
        return 0.5, f"Company size unknown (0.5/{max_score})"

    if any(s in size for s in config.COMPANY_SIZE_SMALL):
        return max_score, f"Small company ({max_score}/{max_score})"
    if any(s in size for s in config.COMPANY_SIZE_MEDIUM):
        return max_score, f"Medium company ({max_score}/{max_score})"
    if any(s in size for s in config.COMPANY_SIZE_LARGE):
        return 0.5, f"Large company (0.5/{max_score})"

    return 0.5, f"Company size: {size} (0.5/{max_score})"


def _score_industry(job):
    """Score 0-1.0 based on industry alignment."""
    text = _text_lower(job)
    industry = (job.industry or "").lower()
    combined = f"{text} {industry}"
    max_score = 1.0

    if any(kw in combined for kw in config.INDUSTRY_RISK_MGMT):
        return max_score, f"Risk management ({max_score}/{max_score})"
    if any(kw in combined for kw in config.INDUSTRY_FINSERV):
        return 0.7, f"Financial services (0.7/{max_score})"
    if any(kw in combined for kw in config.INDUSTRY_INSURANCE):
        return 0.2, f"Insurance carrier (0.2/{max_score})"

    return 0.4, f"General industry (0.4/{max_score})"


def _score_seniority(job):
    """Score 0-1.0 based on seniority fit."""
    title = _title_lower(job)
    text = _text_lower(job)
    max_score = 1.0

    if any(kw in title for kw in config.SENIORITY_EXECUTIVE):
        return 0.2, f"Executive level (0.2/{max_score})"
    if any(kw in title for kw in config.SENIORITY_ENTRY):
        return 0.3, f"Entry level (0.3/{max_score})"
    if any(kw in title for kw in config.SENIORITY_DIRECTOR):
        return 0.7, f"Director level (0.7/{max_score})"
    if any(kw in title for kw in config.SENIORITY_MID_SENIOR):
        return max_score, f"Mid-senior level ({max_score}/{max_score})"

    # Check description for seniority clues
    if any(kw in text for kw in config.SENIORITY_MID_SENIOR):
        return 0.8, f"Mid-senior (from desc) (0.8/{max_score})"

    return 0.5, f"Seniority unclear (0.5/{max_score})"


def _classify_employment_type(job):
    """Classify as Full-time, Part-time, or Contract."""
    if job.job_type:
        jt = job.job_type.lower()
        if "contract" in jt or "freelance" in jt:
            return "Contract"
        if "part" in jt:
            return "Part-time"
        if "full" in jt:
            return "Full-time"

    text = _text_lower(job)
    if "contract" in text or "freelance" in text or "1099" in text:
        return "Contract"
    if "part-time" in text or "part time" in text:
        return "Part-time"
    return "Full-time"


def score_job(raw_job):
    """Score a single job against Will's profile. Returns a ScoredJob."""
    # Check dealbreakers first
    dealbreaker_reasons = _detect_dealbreakers(raw_job)
    red_flags = _detect_red_flags(raw_job)

    if dealbreaker_reasons:
        work_type, _, _ = _classify_work_arrangement(raw_job)
        emp_type = _classify_employment_type(raw_job)
        return ScoredJob(
            raw=raw_job,
            score=0.0,
            score_breakdown={"dealbreaker": dealbreaker_reasons},
            explanation=f"0.0/10: DEALBREAKER — {'; '.join(dealbreaker_reasons)}",
            red_flags=dealbreaker_reasons + red_flags,
            is_dealbreaker=True,
            work_type=work_type,
            employment_type=emp_type,
            priority="Low",
        )

    # Score each dimension
    role_score, role_expl = _score_role_type(raw_job)
    skills_score, skills_expl = _score_skills(raw_job)
    work_type, work_score, work_expl = _classify_work_arrangement(raw_job)
    size_score, size_expl = _score_company_size(raw_job)
    industry_score, industry_expl = _score_industry(raw_job)
    seniority_score, seniority_expl = _score_seniority(raw_job)

    # Apply weights (scores are already on their max scale, weights distribute to 10.0)
    weights = config.WEIGHTS
    weighted_score = (
        role_score * (weights["role_type"] / 0.30) * weights["role_type"] * 10 / 3.0 +
        skills_score * (weights["skills"] / 0.20) * weights["skills"] * 10 / 2.0 +
        work_score * (weights["work_arrangement"] / 0.20) * weights["work_arrangement"] * 10 / 2.0 +
        size_score * (weights["company_size"] / 0.10) * weights["company_size"] * 10 / 1.0 +
        industry_score * (weights["industry"] / 0.10) * weights["industry"] * 10 / 1.0 +
        seniority_score * (weights["seniority"] / 0.10) * weights["seniority"] * 10 / 1.0
    )

    # Simplify: each dimension's contribution = (score / max_score) * weight * 10
    total = round(
        (role_score / 3.0) * weights["role_type"] * 10 +
        (skills_score / 2.0) * weights["skills"] * 10 +
        (work_score / 2.0) * weights["work_arrangement"] * 10 +
        (size_score / 1.0) * weights["company_size"] * 10 +
        (industry_score / 1.0) * weights["industry"] * 10 +
        (seniority_score / 1.0) * weights["seniority"] * 10,
        1,
    )

    breakdown = {
        "role_type": role_score,
        "skills": skills_score,
        "work_arrangement": work_score,
        "company_size": size_score,
        "industry": industry_score,
        "seniority": seniority_score,
    }

    explanation = f"{total}/10: {role_expl} | {skills_expl} | {work_expl} | {size_expl} | {industry_expl} | {seniority_expl}"

    emp_type = _classify_employment_type(raw_job)

    if total >= 7:
        priority = "High"
    elif total >= 5:
        priority = "Medium"
    else:
        priority = "Low"

    return ScoredJob(
        raw=raw_job,
        score=total,
        score_breakdown=breakdown,
        explanation=explanation,
        red_flags=red_flags,
        is_dealbreaker=False,
        work_type=work_type,
        employment_type=emp_type,
        priority=priority,
    )
