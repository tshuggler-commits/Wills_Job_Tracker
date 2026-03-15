"""
Location filter for Will's job discovery pipeline.

Runs after source fetch, before dedup. Rejects jobs that clearly
can't be filled from Georgia, US. Two checks:

1. Non-Latin character detection (catches CJK, Cyrillic, Arabic, etc.)
2. Location string validation (catches explicitly non-US locations)

Ambiguous cases pass through to scoring for further evaluation.
"""

import re
from typing import List

from discovery.sources.base import RawJob


# --- Character detection ---

_LATIN_PATTERN = re.compile(r'^[\u0000-\u024F\u1E00-\u1EFF\s\d\W]+$')


def contains_non_latin(text: str) -> bool:
    """Returns True if text contains non-Latin script characters.

    Catches Chinese, Japanese, Korean, Cyrillic, Arabic, Devanagari,
    and other non-Latin scripts. Allows extended Latin (accented chars
    used in French, Spanish, Portuguese, etc.).
    """
    if not text:
        return False
    return not _LATIN_PATTERN.match(text)


# --- Location validation ---

NON_US_SIGNALS = [
    # Country names and codes
    "UK", "United Kingdom", "Canada", "India", "Germany", "France",
    "Australia", "Japan", "China", "Singapore", "Brazil", "Mexico",
    "Netherlands", "Ireland", "Spain", "Italy", "Sweden", "Norway",
    "Denmark", "Switzerland", "Israel", "UAE", "Dubai", "Poland",
    "Philippines", "Vietnam", "Thailand", "Indonesia", "Malaysia",
    "South Korea", "Taiwan", "Hong Kong", "New Zealand", "Argentina",
    "Colombia", "Czech Republic", "Romania", "Portugal", "Belgium",
    "Austria", "Finland", "Nigeria", "Kenya", "South Africa",
    "Saudi Arabia", "Qatar", "Bahrain", "Pakistan", "Bangladesh",
    "Sri Lanka", "Egypt", "Turkey", "Greece", "Hungary",
    # Region patterns
    "Europe", "EMEA", "APAC", "LATAM", "Asia-Pacific",
    "Middle East", "Africa",
    # Non-US city names that appear often in remote job listings
    "London", "Berlin", "Paris", "Toronto", "Vancouver", "Mumbai",
    "Bangalore", "Hyderabad", "Sydney", "Melbourne", "Dublin",
    "Amsterdam", "Stockholm", "Copenhagen", "Zurich", "Tel Aviv",
    "São Paulo", "Buenos Aires", "Lagos", "Nairobi", "Cape Town",
]

US_SIGNALS = [
    "United States", "USA", "U.S.", "US",
    # Georgia and Atlanta metro
    "Georgia", "Atlanta", "GA",
    # Common remote indicators (no country = assume US-eligible)
    "Remote", "Anywhere", "Distributed",
    # Other US states/cities that show up in Will's target roles
    "New York", "NY", "California", "CA", "Texas", "TX",
    "Florida", "FL", "Illinois", "IL", "Virginia", "VA",
    "North Carolina", "NC", "Ohio", "OH", "Pennsylvania", "PA",
    "Massachusetts", "MA", "Washington", "WA", "Colorado", "CO",
    "Arizona", "AZ", "Tennessee", "TN", "Maryland", "MD",
    "New Jersey", "NJ", "Connecticut", "CT",
]

_NON_US_UPPER = [s.upper() for s in NON_US_SIGNALS]
_US_UPPER = [s.upper() for s in US_SIGNALS]


def has_us_signal(location: str) -> bool:
    """Returns True only if location explicitly mentions US/Remote/state.

    Unlike is_us_eligible (which passes ambiguous locations through),
    this returns False for ambiguous locations. Used by scoring to
    penalize unconfirmed locations.
    """
    if not location:
        return False

    loc_upper = location.upper()
    for signal in _US_UPPER:
        if signal in loc_upper:
            return True
    return False


def is_us_eligible(location: str) -> bool:
    """Returns True if the job appears fillable from Georgia, US."""
    if not location:
        return True

    loc_upper = location.upper()

    # Check US-positive signals first
    for signal in _US_UPPER:
        if signal in loc_upper:
            return True

    # Check non-US signals
    for signal in _NON_US_UPPER:
        if signal in loc_upper:
            return False

    # Ambiguous — let scoring deal with it
    return True


# --- Combined filter ---

def passes_location_filter(job: RawJob) -> bool:
    """Returns True if the job should continue through the pipeline."""
    # Check title, company, and location for non-Latin characters
    for field in [job.title, job.company, job.location]:
        if contains_non_latin(field):
            return False

    # Check location string for non-US signals
    if not is_us_eligible(job.location):
        return False

    return True


def filter_jobs(jobs: List[RawJob]) -> tuple[List[RawJob], int]:
    """Filter a list of RawJobs, returning (kept, rejected_count)."""
    kept = [job for job in jobs if passes_location_filter(job)]
    rejected = len(jobs) - len(kept)
    return kept, rejected
