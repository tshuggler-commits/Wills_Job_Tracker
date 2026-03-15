"""
Writes scored jobs to the Notion Job Tracker database.
"""

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

    parts.append(f"\nScore breakdown: {scored_job.explanation}")

    return " | ".join(parts) if len(parts) > 1 else parts[0] if parts else ""


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
    # Notion Red Flags options: Toxic Leadership, High Turnover, Hostile Culture,
    # Low Pay, Scam Risk, Poor Reviews, No Growth
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
            # Default: if the flag contains "toxic", map to Toxic Leadership
            if "toxic" in flag_lower:
                mapped.add("Toxic Leadership")
    return list(mapped)


def _map_industry(industry_str):
    """Map raw industry string to a Notion select option name."""
    if not industry_str:
        return None
    industry_lower = industry_str.lower()
    # Notion Industry options: Risk Management, Financial Services, Insurance,
    # Technology, Consulting, Healthcare, Government
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
    return None  # Don't set if we can't map to a valid option


def write_job(scored_job):
    """Write a single scored job to Notion. Returns the created page or None on failure."""
    salary = _build_salary_text(scored_job)
    intel = _build_intel_string(scored_job)
    company_size = _map_company_size(scored_job)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    properties = {
        "Job Title": {"title": [{"text": {"content": scored_job.raw.title[:2000]}}]},
        "Company": {"rich_text": [{"text": {"content": scored_job.raw.company[:2000]}}]},
        "Match Score": {"number": scored_job.score},
        "Work Type": {"select": {"name": scored_job.work_type}},
        "Employment Type": {"select": {"name": scored_job.employment_type}},
        "Date Found": {"date": {"start": today}},
        "Source": {"select": {"name": scored_job.raw.source}},
        "Priority": {"select": {"name": scored_job.priority}},
        "Status": {"select": {"name": "Rejected" if scored_job.is_dealbreaker else "New"}},
    }

    # Optional fields — only add if we have data
    if salary:
        properties["Salary Range"] = {"rich_text": [{"text": {"content": salary[:2000]}}]}
    if scored_job.raw.apply_link:
        properties["Apply Link"] = {"url": scored_job.raw.apply_link}
    if intel:
        properties["Company Intel"] = {"rich_text": [{"text": {"content": intel[:2000]}}]}
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
        print(f"  ✓ Written: {scored_job.raw.title} @ {scored_job.raw.company} (score: {scored_job.score})")
        time.sleep(0.4)  # Respect Notion rate limit (3 req/sec)
        return result
    except Exception as e:
        print(f"  ✗ Failed to write: {scored_job.raw.title} @ {scored_job.raw.company}: {e}")
        return None
