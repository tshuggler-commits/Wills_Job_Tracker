#!/usr/bin/env python3
"""
One-time backfill script for legacy unscored jobs.

Queries Notion for jobs where Total Score is null, Status is New or Reviewing,
and Dismissed is false. Runs each through the same dual-scoring pipeline used
by the discovery engine and writes all 9 scoring fields back to Notion.

Usage:
    python scripts/backfill_scores.py                # Run for real
    python scripts/backfill_scores.py --dry-run      # Log what would be scored

Environment variables required:
    NOTION_TOKEN       - Notion integration token
    ANTHROPIC_API_KEY  - Anthropic API key for scoring
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

# Add repo root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from notion_common import (
    query_database,
    extract_property,
    update_page,
    NOTION_DATABASE_ID,
)

# Load Will's profile
_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "discovery", "data", "will-profile.json")
with open(_PROFILE_PATH, "r") as f:
    WILL_PROFILE = json.load(f)
WILL_PROFILE_JSON = json.dumps(WILL_PROFILE, indent=2)

# Load the scoring prompt template
from importlib.util import spec_from_file_location, module_from_spec
_template_path = os.path.join(os.path.dirname(__file__), "..", "scoring-prompt-template.py")
_spec = spec_from_file_location("scoring_prompt_template", _template_path)
_template_module = module_from_spec(_spec)
_spec.loader.exec_module(_template_module)
SCORING_SYSTEM_PROMPT = _template_module.SCORING_SYSTEM_PROMPT
SCORING_USER_PROMPT = _template_module.SCORING_USER_PROMPT

# Min score threshold (for logging only — we still write all scores)
MIN_SCORE_THRESHOLD = 5.0


def _get_unscored_jobs():
    """Query Notion for jobs that need scoring."""
    print("Querying Notion for unscored jobs...")

    # Filter: Total Score is empty AND Status is New or Reviewing AND Dismissed is false
    filter_obj = {
        "and": [
            {
                "property": "Total Score",
                "number": {"is_empty": True},
            },
            {
                "or": [
                    {"property": "Status", "select": {"equals": "New"}},
                    {"property": "Status", "select": {"equals": "Reviewing"}},
                ],
            },
            {
                "property": "Dismissed",
                "checkbox": {"equals": False},
            },
        ]
    }

    pages = query_database(NOTION_DATABASE_ID, filter_obj=filter_obj)
    print(f"  Found {len(pages)} unscored jobs")
    return pages


def _call_anthropic(title, company, location, salary, employment_type, description):
    """Send job data to Claude for dual scoring. Returns parsed dict or None."""
    import anthropic

    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    user_prompt = SCORING_USER_PROMPT.format(
        job_title=title,
        company=company,
        location=location or "Not specified",
        salary=salary or "Not listed",
        employment_type=employment_type or "Not specified",
        description=description[:4000] if description else "No description available",
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
        print(f"    JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    API error: {e}")
        return None


def _rich_text(content, max_len=2000):
    """Build a Notion rich_text property value."""
    if not content:
        return {"rich_text": []}
    text = str(content)[:max_len]
    return {"rich_text": [{"text": {"content": text}}]}


def _json_rich_text(obj, max_len=2000):
    """Serialize a dict/list to JSON and wrap as rich_text."""
    if not obj:
        return {"rich_text": []}
    text = json.dumps(obj, indent=2)[:max_len]
    return {"rich_text": [{"text": {"content": text}}]}


def _build_update_properties(result):
    """Build Notion property update payload from API result."""
    fit_score = float(result.get("fit_score", 0))
    match_score = float(result.get("match_score", 0))
    total_score = float(result.get("total_score", 0))

    properties = {
        "Fit Score": {"number": round(fit_score, 1)},
        "Match Score": {"number": round(match_score, 1)},
        "Total Score": {"number": round(total_score, 1)},
    }

    # Role Summary
    role_summary = result.get("role_summary", "")
    if role_summary:
        properties["Role Summary"] = _rich_text(role_summary)

    # Key Requirements
    key_reqs = result.get("key_requirements", [])
    if key_reqs:
        req_text = "\n".join(f"- {r}" for r in key_reqs)
        properties["Key Requirements"] = _rich_text(req_text)

    # Why Match
    why_match = result.get("why_match", "")
    if why_match:
        properties["Why Match"] = _rich_text(why_match)

    # Skill Gaps
    match_breakdown = result.get("match_breakdown", {})
    skill_gaps = []
    if isinstance(match_breakdown, dict):
        skills_overlap = match_breakdown.get("skills_overlap", {})
        if isinstance(skills_overlap, dict):
            skill_gaps = skills_overlap.get("gaps", [])
    if skill_gaps:
        properties["Skill Gaps"] = _rich_text(", ".join(skill_gaps))

    # Fit Breakdown (JSON string)
    fit_breakdown = result.get("fit_breakdown", {})
    if fit_breakdown:
        properties["Fit Breakdown"] = _json_rich_text(fit_breakdown)

    # Match Breakdown (JSON string)
    if match_breakdown:
        properties["Match Breakdown"] = _json_rich_text(match_breakdown)

    # Update Priority based on total score
    if total_score >= 7:
        properties["Priority"] = {"select": {"name": "High"}}
    elif total_score >= 5:
        properties["Priority"] = {"select": {"name": "Medium"}}
    else:
        properties["Priority"] = {"select": {"name": "Low"}}

    return properties, total_score


def main():
    parser = argparse.ArgumentParser(description="Backfill scores for legacy unscored jobs")
    parser.add_argument("--dry-run", action="store_true", help="Log what would be scored without making API calls")
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — no API calls or Notion writes will be made")
        print("=" * 60)
    else:
        print("=" * 60)
        print("BACKFILL SCORING — LIVE RUN")
        print("=" * 60)

    # Verify env vars
    if not os.environ.get("NOTION_TOKEN"):
        print("Error: NOTION_TOKEN not set")
        sys.exit(1)
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Get unscored jobs
    jobs = _get_unscored_jobs()
    if not jobs:
        print("No unscored jobs found. Nothing to do.")
        return

    scored_count = 0
    below_threshold = 0
    error_count = 0

    for i, page in enumerate(jobs):
        page_id = page["id"]
        title = extract_property(page, "Job Title")
        company = extract_property(page, "Company")
        location = extract_property(page, "Work Type")  # May have location info
        salary = extract_property(page, "Salary Range")
        emp_type = extract_property(page, "Employment Type")
        role_summary_existing = extract_property(page, "Role Summary")

        label = f"{title} @ {company}"
        print(f"\n[{i+1}/{len(jobs)}] {label}")

        if args.dry_run:
            print(f"  Would score this job (Title: {title}, Company: {company})")
            continue

        # Build a description from available Notion data
        # Legacy jobs may not have a full description stored, so we use what we have
        description_parts = []
        if title:
            description_parts.append(f"Job Title: {title}")
        if company:
            description_parts.append(f"Company: {company}")
        if salary:
            description_parts.append(f"Salary: {salary}")
        if emp_type:
            description_parts.append(f"Employment Type: {emp_type}")
        company_intel = extract_property(page, "Company Intel")
        if company_intel:
            description_parts.append(f"Company Info: {company_intel}")

        description = "\n".join(description_parts)

        # Call Anthropic API
        result = _call_anthropic(title, company, location, salary, emp_type, description)

        if result is None:
            print(f"  FAILED — skipping")
            error_count += 1
            continue

        # Build and write properties
        properties, total_score = _build_update_properties(result)

        try:
            update_page(page_id, properties)
            scored_count += 1

            flag = ""
            if total_score < MIN_SCORE_THRESHOLD:
                below_threshold += 1
                flag = " [BELOW THRESHOLD]"

            print(f"  Fit: {result.get('fit_score', '?')}, "
                  f"Match: {result.get('match_score', '?')}, "
                  f"Total: {total_score}{flag}")

        except Exception as e:
            print(f"  Notion write FAILED: {e}")
            error_count += 1

        # Rate limit: ~2 sec between API calls
        time.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)
    print(f"  Total unscored jobs found:  {len(jobs)}")
    if args.dry_run:
        print(f"  Would score:                {len(jobs)}")
    else:
        print(f"  Successfully scored:        {scored_count}")
        print(f"  Below threshold ({MIN_SCORE_THRESHOLD}):     {below_threshold}")
        print(f"  Errors:                     {error_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
