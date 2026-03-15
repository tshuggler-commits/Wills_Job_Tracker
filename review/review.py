"""
Job Status Review + Archive Pipeline — CLI entry point.

Checks existing jobs for expiration and archives closed ones.

Usage:
    python -m review.review run

Environment variables required:
    NOTION_TOKEN           - Notion integration token
    NOTION_DATABASE_ID     - Active Job Tracker database ID
    NOTION_ARCHIVE_DB_ID   - Archive database ID
"""

import sys
import os
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import (
    query_database, extract_property, extract_job,
    NOTION_DATABASE_ID, NOTION_ARCHIVE_DB_ID,
)
from .link_checker import check_link
from .archiver import archive_job

# Import location filter for catching non-US jobs already in tracker
from discovery.location_filter import contains_non_latin, is_us_eligible


# Statuses that mean Will is actively pursuing the job — don't touch these
PROTECTED_STATUSES = {"Applied", "Interview", "Offer", "Rejected", "Withdrawn"}

# Age threshold for age-based expiry (days)
STALE_THRESHOLD_DAYS = 30


def _get_jobs_to_review():
    """Query active tracker for unacted-on jobs that need status review."""
    print("Querying active tracker for jobs to review...")

    # Fetch all jobs, filter in Python to avoid complex Notion filter nesting
    all_jobs = query_database(NOTION_DATABASE_ID)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reviewable = []

    for page in all_jobs:
        status = extract_property(page, "Status")
        date_found = extract_property(page, "Date Found")
        dismissed = extract_property(page, "Dismissed")

        # Dismissed jobs always get reviewed (regardless of status)
        if dismissed:
            reviewable.append(page)
            continue

        # Skip protected statuses
        if status in PROTECTED_STATUSES:
            continue

        # Skip jobs added today (too new to check)
        if date_found == today:
            continue

        reviewable.append(page)

    print(f"  Found {len(reviewable)} jobs to review (skipped {len(all_jobs) - len(reviewable)} protected/new)")
    return reviewable


def _check_job(page):
    """
    Run two-step verification on a job.

    Returns:
        ("OPEN", None)            — job is still active
        ("CLOSED", close_reason)  — job should be archived
        ("INCONCLUSIVE", None)    — couldn't determine
    """
    # Check -1: Dismissed by Will (highest priority — archive immediately)
    dismissed = extract_property(page, "Dismissed")
    if dismissed:
        dismissed_reason = extract_property(page, "Dismissed Reason")
        return "CLOSED", dismissed_reason if dismissed_reason else "Dismissed"

    title = extract_property(page, "Job Title")
    company = extract_property(page, "Company")

    # Check 0: Location filter (catch non-US jobs already in tracker)
    for field in [title, company]:
        if contains_non_latin(field):
            return "CLOSED", "Non-US location"

    apply_link = extract_property(page, "Apply Link")
    apply_by = extract_property(page, "Apply By")
    date_found = extract_property(page, "Date Found")

    # Check A: Link verification
    if apply_link:
        status, reason = check_link(apply_link)
        if status == "CLOSED":
            return "CLOSED", "Link dead"
        if status == "OPEN":
            # Link is live — but still check deadline
            if apply_by:
                try:
                    deadline = datetime.strptime(apply_by, "%Y-%m-%d").date()
                    if deadline < datetime.now(timezone.utc).date():
                        return "CLOSED", "Past deadline"
                except ValueError:
                    pass
            return "OPEN", None
        # INCONCLUSIVE — fall through to Check B
    else:
        # No link — go straight to Check B
        pass

    # Check B: Age-based fallback
    if apply_by:
        try:
            deadline = datetime.strptime(apply_by, "%Y-%m-%d").date()
            if deadline < datetime.now(timezone.utc).date():
                return "CLOSED", "Past deadline"
        except ValueError:
            pass

    if date_found:
        try:
            found_date = datetime.strptime(date_found, "%Y-%m-%d").date()
            age_days = (datetime.now(timezone.utc).date() - found_date).days
            if age_days > STALE_THRESHOLD_DAYS:
                return "CLOSED", "Age-based expiry"
        except ValueError:
            pass

    return "INCONCLUSIVE", None


def run():
    """Full status review + archive pipeline."""
    print("=" * 60)
    print("JOB STATUS REVIEW + ARCHIVE")
    print("=" * 60)

    if not NOTION_ARCHIVE_DB_ID:
        print("Error: NOTION_ARCHIVE_DB_ID not set. Run create_archive_db.py first.")
        sys.exit(1)

    # Get jobs to review
    jobs = _get_jobs_to_review()
    if not jobs:
        print("No jobs to review.")
        return

    # Review each job
    open_count = 0
    archived = []
    inconclusive_count = 0
    errors = []

    for i, page in enumerate(jobs):
        title = extract_property(page, "Job Title")
        company = extract_property(page, "Company")
        label = f"{title} @ {company}"

        print(f"\n[{i+1}/{len(jobs)}] Checking: {label}")

        status, close_reason = _check_job(page)

        if status == "OPEN":
            print(f"  → Still open")
            open_count += 1

        elif status == "CLOSED":
            print(f"  → Closed: {close_reason}")
            success, error = archive_job(page, close_reason)
            if success:
                archived.append((label, close_reason))
            else:
                errors.append(f"{label}: {error}")

        else:  # INCONCLUSIVE
            print(f"  → Inconclusive (leaving in active tracker)")
            inconclusive_count += 1

        # Rate limit between link checks
        time.sleep(2.5)

    # Summary
    print("\n" + "=" * 60)
    print("REVIEW SUMMARY")
    print("=" * 60)
    print(f"  Total reviewed:      {len(jobs)}")
    print(f"  Still open:          {open_count}")
    print(f"  Archived:            {len(archived)}")
    if archived:
        for label, reason in archived:
            print(f"    - {label} ({reason})")
    print(f"  Inconclusive:        {inconclusive_count}")
    if errors:
        print(f"  Errors:              {len(errors)}")
        for e in errors:
            print(f"    ! {e}")
    print("=" * 60)


def main():
    commands = {
        "run": run,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Usage: python -m review.review <{'|'.join(commands.keys())}>")
        sys.exit(1)

    command = sys.argv[1]
    print(f"Running: {command}")
    commands[command]()
    print("Done.")


if __name__ == "__main__":
    main()
