"""
Job Discovery Pipeline — CLI entry point.

Usage:
    python -m discovery.discover run            # Full discovery pipeline
    python -m discovery.discover test-scoring   # Test scoring with mock jobs

Environment variables required:
    NOTION_TOKEN         - Notion integration token
    NOTION_DATABASE_ID   - Job Tracker database ID (defaults to production)
    ADZUNA_APP_ID        - Adzuna API app ID (optional, skipped if missing)
    ADZUNA_APP_KEY       - Adzuna API app key (optional, skipped if missing)
"""

import sys
import os

# Ensure parent directory is on path for notion_common imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .sources.adzuna import AdzunaSource
from .sources.remotive import RemotiveSource
from .sources.themuse import TheMuseSource
from .sources.jobspy_source import JobSpySource
from .sources.base import RawJob
from .scoring import score_job
from .dedup import load_existing_keys, generate_dedup_key
from .notion_writer import write_job
from .location_filter import filter_jobs
from . import config


def run():
    """Full discovery pipeline: fetch → dedup → score → write to Notion."""
    print("=" * 60)
    print("JOB DISCOVERY PIPELINE")
    print("=" * 60)

    # Step 1: Load existing jobs for dedup
    existing_keys = load_existing_keys()

    # Step 2: Fetch from all API sources
    sources = [AdzunaSource(), RemotiveSource(), TheMuseSource()]
    all_raw_jobs = []

    for source in sources:
        print(f"\nFetching from {source.name}...")
        for query in config.SEARCH_QUERIES:
            jobs = source.fetch(query, config.LOCATION)
            all_raw_jobs.extend(jobs)

    print(f"\nTotal raw jobs from APIs: {len(all_raw_jobs)}")

    # Step 2b: Location filter (remove non-US / non-Latin jobs)
    all_raw_jobs, location_filtered = filter_jobs(all_raw_jobs)
    if location_filtered:
        print(f"  Location filter removed {location_filtered} jobs")

    # Step 3: Dedup against Notion + intra-run
    new_jobs = []
    seen_keys = set()
    dupes_skipped = 0

    for job in all_raw_jobs:
        key = generate_dedup_key(job.title, job.company)
        if key in existing_keys or key in seen_keys:
            dupes_skipped += 1
            continue
        seen_keys.add(key)
        new_jobs.append(job)

    print(f"After dedup: {len(new_jobs)} new, {dupes_skipped} duplicates skipped")

    # Step 4: JobSpy fallback if fewer than threshold
    if len(new_jobs) < config.JOBSPY_FALLBACK_THRESHOLD:
        print(f"\nFewer than {config.JOBSPY_FALLBACK_THRESHOLD} new jobs — running JobSpy fallback...")
        jobspy = JobSpySource()
        for query in config.SEARCH_QUERIES[:3]:  # Limit to top 3 queries for speed
            jobs = jobspy.fetch(query, config.LOCATION)
            for job in jobs:
                key = generate_dedup_key(job.title, job.company)
                if key not in existing_keys and key not in seen_keys:
                    seen_keys.add(key)
                    new_jobs.append(job)

        print(f"After JobSpy fallback: {len(new_jobs)} new total")

    # Step 5: Score all new jobs
    print(f"\nScoring {len(new_jobs)} jobs...")
    scored_jobs = [score_job(job) for job in new_jobs]

    # Step 6: Filter and write
    written = 0
    filtered = 0
    dealbreakers = 0
    errors = 0

    for sj in scored_jobs:
        if sj.is_dealbreaker:
            dealbreakers += 1
            print(f"  ✗ Dealbreaker: {sj.raw.title} @ {sj.raw.company} — {sj.explanation}")
            # Don't write to Notion — zero-score jobs never reach the tracker
        elif sj.score < config.MIN_SCORE_THRESHOLD:
            filtered += 1
            print(f"  - Filtered (score {sj.score}): {sj.raw.title} @ {sj.raw.company}")
        else:
            result = write_job(sj)
            if result:
                written += 1
            else:
                errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("DISCOVERY SUMMARY")
    print("=" * 60)
    print(f"  Raw jobs fetched:    {len(all_raw_jobs) + location_filtered}")
    print(f"  Location filtered:   {location_filtered}")
    print(f"  Duplicates skipped:  {dupes_skipped}")
    print(f"  New jobs scored:     {len(new_jobs)}")
    print(f"  Written to Notion:   {written}")
    print(f"  Below threshold:     {filtered}")
    print(f"  Dealbreakers:        {dealbreakers}")
    if errors:
        print(f"  Write errors:        {errors}")
    print("=" * 60)

    return written


def test_scoring():
    """Test the scoring engine with sample mock jobs."""
    print("Testing scoring engine with mock jobs...\n")

    test_jobs = [
        RawJob(
            title="Operations Manager",
            company="Risk Solutions Inc",
            location="Atlanta, GA (Remote)",
            description="We're looking for an operations manager to lead process improvement and automation initiatives. Experience with RPA, stakeholder management, and change management required. Financial services background preferred. Risk management experience a plus.",
            apply_link="https://example.com/job1",
            source="Test",
            is_remote=True,
            company_size="51-200",
            industry="Risk Management",
        ),
        RawJob(
            title="Junior Data Entry Clerk",
            company="Big Corp Insurance",
            location="New York, NY",
            description="Entry-level position. Must be in office 5 days a week. No remote work. 25% travel required.",
            apply_link="https://example.com/job2",
            source="Test",
            is_remote=False,
            company_size="10001+",
            industry="Insurance",
        ),
        RawJob(
            title="Business Analyst - Process Improvement",
            company="FinTech Startup",
            location="Flexible / Remote",
            description="Looking for a business analyst with experience in requirements gathering, data migration, and process optimization. Startup environment, wear many hats, work like a family.",
            apply_link="https://example.com/job3",
            source="Test",
            is_remote=True,
            company_size="11-50",
            industry="Financial Technology",
        ),
        RawJob(
            title="Program Manager, Automation",
            company="MidSize FinServ Co",
            location="Atlanta, GA (Hybrid)",
            description="Lead automation programs across business units. Experience with project management, stakeholder management, and compliance operations. 5+ years experience required.",
            apply_link="https://example.com/job4",
            source="Test",
            company_size="201-500",
            industry="Financial Services",
        ),
    ]

    for job in test_jobs:
        scored = score_job(job)
        print(f"{'=' * 50}")
        print(f"Title:      {job.title}")
        print(f"Company:    {job.company}")
        print(f"Location:   {job.location}")
        print(f"Score:      {scored.score}/10 [{scored.priority}]")
        print(f"Work Type:  {scored.work_type}")
        print(f"Emp Type:   {scored.employment_type}")
        if scored.is_dealbreaker:
            print(f"DEALBREAKER: {', '.join(scored.red_flags)}")
        elif scored.red_flags:
            print(f"Red Flags:  {', '.join(scored.red_flags)}")
        print(f"Breakdown:  {scored.explanation}")
        print()


def main():
    commands = {
        "run": run,
        "test-scoring": test_scoring,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Usage: python -m discovery.discover <{'|'.join(commands.keys())}>")
        sys.exit(1)

    command = sys.argv[1]
    print(f"Running: {command}")
    commands[command]()
    print("Done.")


if __name__ == "__main__":
    main()
