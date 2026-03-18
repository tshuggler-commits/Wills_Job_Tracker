"""
Job scoring engine — dual scoring via Anthropic API.

Sends each job posting + Will's profile to Claude and gets back:
- Fit Score (1-10): preference match
- Match Score (1-10): skills/qualification match
- Total Score: (Fit x 0.4) + (Match x 0.6)
- Role summary, key requirements, why match, skill gaps, breakdowns

On-site dealbreaker is checked locally first (never hits the API).
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from .sources.base import RawJob
from .location_filter import has_us_signal
from . import config

# Load Will's profile once at module level
_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "data", "will-profile.json")
with open(_PROFILE_PATH, "r") as f:
    WILL_PROFILE = json.load(f)
WILL_PROFILE_JSON = json.dumps(WILL_PROFILE, indent=2)

# Import the scoring prompt template
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from importlib.util import spec_from_file_location, module_from_spec
_template_path = os.path.join(os.path.dirname(__file__), "..", "scoring-prompt-template.py")
_spec = spec_from_file_location("scoring_prompt_template", _template_path)
_template_module = module_from_spec(_spec)
_spec.loader.exec_module(_template_module)
SCORING_SYSTEM_PROMPT = _template_module.SCORING_SYSTEM_PROMPT
SCORING_USER_PROMPT = _template_module.SCORING_USER_PROMPT

# Anthropic client
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    return _client


@dataclass
class ScoredJob:
    """A job with its dual scores and extracted metadata."""
    raw: RawJob
    fit_score: float
    match_score: float
    total_score: float
    fit_breakdown: dict
    match_breakdown: dict
    role_summary: str
    key_requirements: list
    why_match: str
    skill_gaps: list
    red_flags: list
    is_dealbreaker: bool
    work_type: str       # "Remote", "Hybrid", "On-site"
    employment_type: str  # "Full-time", "Part-time", "Contract"
    priority: str        # "High", "Medium", "Low"
    potential_concerns: Optional[str] = None

    @property
    def score(self):
        """Backward compatibility — total_score is the primary sort score."""
        return self.total_score


# ---------------------------------------------------------------------------
# Local pre-checks (avoid API calls for obvious dealbreakers)
# ---------------------------------------------------------------------------

def _text_lower(job):
    return f"{job.title} {job.description} {job.location}".lower()


def _is_onsite_dealbreaker(job):
    """Quick local check: is this clearly on-site? Returns True if dealbreaker."""
    text = _text_lower(job)

    # Check for explicit on-site signals
    onsite_patterns = [
        r"on[\-\s]site\s+(required|only|mandatory)",
        r"must\s+be\s+in\s+office",
        r"in[\-\s]office\s+only",
        r"not\s+remote",
        r"no\s+remote",
    ]
    has_onsite_strict = any(re.search(p, text, re.IGNORECASE) for p in onsite_patterns)

    if has_onsite_strict:
        # Allow if it's in Atlanta metro
        is_atlanta = any(kw in text for kw in config.ATLANTA_KEYWORDS)
        if not is_atlanta:
            return True

    # Check for on-site keywords without remote/hybrid signals
    onsite_kws = ["on-site", "onsite", "in-office", "in office"]
    remote_kws = ["remote", "work from home", "wfh", "telecommute", "hybrid", "flexible"]

    has_onsite = any(kw in text for kw in onsite_kws)
    has_remote = any(kw in text for kw in remote_kws) or job.is_remote

    if has_onsite and not has_remote:
        is_atlanta = any(kw in text for kw in config.ATLANTA_KEYWORDS)
        if not is_atlanta:
            return True

    return False


def _detect_travel_dealbreaker(job):
    """Check if travel is required (dealbreaker)."""
    text = _text_lower(job)
    for p in config.DEALBREAKER_TRAVEL:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _classify_work_arrangement(job):
    """Classify as Remote/Hybrid/On-site for metadata."""
    text = _text_lower(job)
    has_anti_remote = any(kw in text for kw in config.ONSITE_KEYWORDS)

    if not has_anti_remote and (job.is_remote or any(kw in text for kw in config.REMOTE_KEYWORDS)):
        return "Remote"
    if any(kw in text for kw in config.HYBRID_KEYWORDS):
        return "Hybrid"
    return "On-site"


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


# ---------------------------------------------------------------------------
# API scoring
# ---------------------------------------------------------------------------

def _build_salary_text(job):
    """Build salary string for the prompt."""
    if job.salary_text:
        return job.salary_text
    if job.salary_min and job.salary_max:
        return f"${job.salary_min:,.0f} - ${job.salary_max:,.0f}"
    if job.salary_min:
        return f"${job.salary_min:,.0f}+"
    return "Not listed"


def _call_anthropic(job):
    """Send job + profile to Claude for dual scoring. Returns parsed dict or None."""
    client = _get_client()

    user_prompt = SCORING_USER_PROMPT.format(
        job_title=job.title,
        company=job.company,
        location=job.location or "Not specified",
        salary=_build_salary_text(job),
        employment_type=job.job_type or "Not specified",
        description=job.description[:4000],  # Cap description length
        profile_json=WILL_PROFILE_JSON,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SCORING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = response.content[0].text.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        return json.loads(content)

    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error for {job.title} @ {job.company}: {e}")
        return None
    except anthropic.APIError as e:
        print(f"  ⚠ Anthropic API error for {job.title} @ {job.company}: {e}")
        return None
    except Exception as e:
        print(f"  ⚠ Unexpected error scoring {job.title} @ {job.company}: {e}")
        return None


def _make_dealbreaker_job(raw_job, reason):
    """Create a zero-score ScoredJob for dealbreakers."""
    work_type = _classify_work_arrangement(raw_job)
    emp_type = _classify_employment_type(raw_job)
    return ScoredJob(
        raw=raw_job,
        fit_score=0.0,
        match_score=0.0,
        total_score=0.0,
        fit_breakdown={},
        match_breakdown={},
        role_summary="",
        key_requirements=[],
        why_match="",
        skill_gaps=[],
        red_flags=[reason],
        is_dealbreaker=True,
        work_type=work_type,
        employment_type=emp_type,
        priority="Low",
    )


def score_job(raw_job):
    """Score a single job against Will's profile using the Anthropic API.

    Returns a ScoredJob with dual scores and extracted metadata.
    """
    # Local dealbreaker checks (skip API call)
    if _is_onsite_dealbreaker(raw_job):
        return _make_dealbreaker_job(raw_job, "On-site work arrangement")

    if _detect_travel_dealbreaker(raw_job):
        return _make_dealbreaker_job(raw_job, "Travel required")

    # Call Anthropic API for dual scoring
    result = _call_anthropic(raw_job)

    if result is None:
        # API failed — return a low score so it doesn't get written
        return _make_dealbreaker_job(raw_job, "Scoring API error")

    # Check if API flagged on-site dealbreaker
    fit_score = float(result.get("fit_score", 0))
    match_score = float(result.get("match_score", 0))
    total_score = float(result.get("total_score", 0))

    if total_score == 0 and fit_score == 0:
        return _make_dealbreaker_job(raw_job, "On-site dealbreaker (API)")

    # Extract all fields
    fit_breakdown = result.get("fit_breakdown", {})
    match_breakdown = result.get("match_breakdown", {})
    role_summary = result.get("role_summary", "")
    key_requirements = result.get("key_requirements", [])
    why_match = result.get("why_match", "")
    potential_concerns = result.get("potential_concerns")

    # Extract skill gaps from match_breakdown
    skill_gaps = []
    if isinstance(match_breakdown, dict):
        skills_overlap = match_breakdown.get("skills_overlap", {})
        if isinstance(skills_overlap, dict):
            skill_gaps = skills_overlap.get("gaps", [])

    # Determine work type and employment type
    work_type = _classify_work_arrangement(raw_job)
    emp_type = _classify_employment_type(raw_job)

    # Override work type from API if available
    if isinstance(fit_breakdown, dict):
        wa = fit_breakdown.get("work_arrangement", {})
        if isinstance(wa, dict):
            api_work_type = wa.get("value", "").strip()
            if api_work_type in ("Remote", "Hybrid", "On-site"):
                work_type = api_work_type

    # Priority based on total score
    if total_score >= 7:
        priority = "High"
    elif total_score >= 5:
        priority = "Medium"
    else:
        priority = "Low"

    # Red flags (from local detection)
    red_flags = []
    text = _text_lower(raw_job)
    for flag_name, patterns in config.RED_FLAG_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                label = flag_name.replace("_", " ").title()
                red_flags.append(label)
                break

    return ScoredJob(
        raw=raw_job,
        fit_score=round(fit_score, 1),
        match_score=round(match_score, 1),
        total_score=round(total_score, 1),
        fit_breakdown=fit_breakdown,
        match_breakdown=match_breakdown,
        role_summary=role_summary,
        key_requirements=key_requirements,
        why_match=why_match,
        skill_gaps=skill_gaps,
        red_flags=red_flags,
        is_dealbreaker=False,
        work_type=work_type,
        employment_type=emp_type,
        priority=priority,
        potential_concerns=potential_concerns,
    )
