"""
Writes scored jobs to the Notion Job Tracker database.

Writes all dual-scoring fields:
- Fit Score, Match Score, Total Score (numbers)
- Role Summary, Key Requirements, Why Match, Skill Gaps (rich text)
- Fit Breakdown, Match Breakdown (rich text, stored as JSON strings)
"""

import json
import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import create_page, NOTION_DATABASE_ID


def _build_salary_text(scored_job):
    """Build a human-readable salary string."""
    raw = scored_job.raw
    if raw.salary_text:
        return raw.salary_text
    if raw.salary_min and raw.salary_max:
        return f"${raw.salary_min:,.0f} - ${raw.salary_max:,.0f}"
    if raw.salary_min:
        return f"${raw.salary_min:,.0f}+"
    return ""


def _build_intel_string(scored_job):
    """Build the Company Intel field content."""
    parts = []

    if scored_job.raw.company_size:
        parts.append(f"Size: {scored_job.raw.company_size}")
    if scored_job.raw.industry:
        parts.append(f"Industry: {scored_job.raw.industry}")
    if scored_job.raw.company_description:
        parts.append(f"About: {scored_job.raw.company_description}")

    return " | ".join(parts) if parts else ""


def _map_company_size(scored_job):
    """Map company size string to a Notion select value."""
    size = (scored_job.raw.company_size or "").lower()
    if not size:
        return None

    small = ["1-50", "1-10", "11-50", "small", "startup"]
    medium = ["51-200", "51-250", "201-500", "medium", "mid-size", "midsize"]
    large = ["501-1000", "1001-5000", "5001-10000", "10001+", "large", "enterprise"]

    if any(s in size for s in small):
        return "Small"
    if any(s in size for s in medium):
        return "Medium"
    if any(s in size for s in large):
        return "Large"
    return None


def _map_red_flags(red_flags):
    """Map pipeline red flag strings to Notion multi_select option names."""
    flag_mapping = {
        "toxic": "Toxic Leadership",
        "travel required": "Hostile Culture",
        "on-site required": "Hostile Culture",
        "overqualification risk": "No Growth",
        "underqualification risk": "No Growth",
        "high pressure signals": "Toxic Leadership",
    }
    mapped = set()
    for flag in red_flags:
        flag_lower = flag.lower()
        for key, notion_option in flag_mapping.items():
            if key in flag_lower:
                mapped.add(notion_option)
                break
        else:
            if "toxic" in flag_lower:
                mapped.add("Toxic Leadership")
    return list(mapped)


def _map_industry(industry_str):
    """Map raw industry string to a Notion select option name."""
    if not industry_str:
        return None
    industry_lower = industry_str.lower()
    mapping = [
        (["risk management", "risk", "grc", "governance"], "Risk Management"),
        (["financial", "fintech", "banking", "capital", "lending", "credit"], "Financial Services"),
        (["insurance", "insurtech", "underwriting"], "Insurance"),
        (["technology", "tech", "software", "saas", "it "], "Technology"),
        (["consulting", "advisory", "professional services"], "Consulting"),
        (["healthcare", "health", "medical", "pharma"], "Healthcare"),
        (["government", "federal", "public sector", "state"], "Government"),
    ]
    for keywords, option_name in mapping:
        if any(kw in industry_lower for kw in keywords):
            return option_name
    return None


def _rich_text(content, max_len=2000):
    """Build a Notion rich_text property value."""
    if not content:
        return None
    text = str(content)[:max_len]
    return {"rich_text": [{"text": {"content": text}}]}


def _json_rich_text(obj, max_len=2000):
    """Serialize a dict/list to JSON and wrap as rich_text."""
    if not obj:
        return None
    text = json.dumps(obj, indent=2)[:max_len]
    return {"rich_text": [{"text": {"content": text}}]}


def write_job(scored_job):
    """Write a single scored job to Notion. Returns the created page or None on failure."""
    salary = _build_salary_text(scored_job)
    intel = _build_intel_string(scored_job)
    company_size = _map_company_size(scored_job)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    properties = {
        "Job Title": {"title": [{"text": {"content": scored_job.raw.title[:2000]}}]},
        "Company": {"rich_text": [{"text": {"content": scored_job.raw.company[:2000]}}]},
        # Dual scoring fields
        "Fit Score": {"number": scored_job.fit_score},
        "Match Score": {"number": scored_job.match_score},
        "Total Score": {"number": scored_job.total_score},
        # Metadata
        "Work Type": {"select": {"name": scored_job.work_type}},
        "Employment Type": {"select": {"name": scored_job.employment_type}},
        "Date Found": {"date": {"start": today}},
        "Source": {"select": {"name": scored_job.raw.source}},
        "Priority": {"select": {"name": scored_job.priority}},
        "Status": {"select": {"name": "Rejected" if scored_job.is_dealbreaker else "New"}},
    }

    # Role detail fields (rich text)
    if scored_job.role_summary:
        properties["Role Summary"] = _rich_text(scored_job.role_summary)
    if scored_job.key_requirements:
        # Store as bullet list string
        req_text = "\n".join(f"- {r}" for r in scored_job.key_requirements)
        properties["Key Requirements"] = _rich_text(req_text)
    if scored_job.why_match:
        properties["Why Match"] = _rich_text(scored_job.why_match)
    if scored_job.skill_gaps:
        gaps_text = ", ".join(scored_job.skill_gaps)
        properties["Skill Gaps"] = _rich_text(gaps_text)

    # Breakdown fields (stored as JSON strings)
    if scored_job.fit_breakdown:
        properties["Fit Breakdown"] = _json_rich_text(scored_job.fit_breakdown)
    if scored_job.match_breakdown:
        properties["Match Breakdown"] = _json_rich_text(scored_job.match_breakdown)

    # Optional fields
    if salary:
        properties["Salary Range"] = _rich_text(salary)
    if scored_job.raw.apply_link:
        properties["Apply Link"] = {"url": scored_job.raw.apply_link}
    if intel:
        properties["Company Intel"] = _rich_text(intel)
    if scored_job.red_flags:
        mapped_flags = _map_red_flags(scored_job.red_flags)
        if mapped_flags:
            properties["Red Flags"] = {"multi_select": [{"name": f} for f in mapped_flags]}
    if company_size:
        properties["Company Size"] = {"select": {"name": company_size}}
    mapped_industry = _map_industry(scored_job.raw.industry)
    if mapped_industry:
        properties["Industry"] = {"select": {"name": mapped_industry}}

    try:
        result = create_page(NOTION_DATABASE_ID, properties)
        print(f"  \u2713 Written: {scored_job.raw.title} @ {scored_job.raw.company} "
              f"(Fit: {scored_job.fit_score}, Match: {scored_job.match_score}, "
              f"Total: {scored_job.total_score})")
        time.sleep(0.4)  # Respect Notion rate limit (3 req/sec)
        return result
    except Exception as e:
        print(f"  \u2717 Failed to write: {scored_job.raw.title} @ {scored_job.raw.company}: {e}")
        return None
