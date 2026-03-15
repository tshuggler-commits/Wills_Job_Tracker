"""
Deduplication logic.
Prevents the same job from being added to Notion twice.
Uses normalized title+company as the dedup key.
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import query_database, extract_property, NOTION_DATABASE_ID, NOTION_ARCHIVE_DB_ID


def normalize(text):
    """Lowercase, strip whitespace, remove punctuation, collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def generate_dedup_key(title, company):
    """Create a deduplication key from title and company."""
    return f"{normalize(title)}|{normalize(company)}"


def _extract_keys_from_pages(pages):
    """Extract dedup keys from a list of Notion pages."""
    keys = set()
    for page in pages:
        title = extract_property(page, "Job Title")
        company = extract_property(page, "Company")
        if title or company:
            keys.add(generate_dedup_key(title, company))
    return keys


def load_existing_keys():
    """Fetch all jobs from active tracker + archive and return a set of dedup keys."""
    print("Loading existing jobs from Notion for deduplication...")

    # Active tracker
    active_pages = query_database(NOTION_DATABASE_ID)
    dedup_keys = _extract_keys_from_pages(active_pages)
    print(f"  Loaded {len(dedup_keys)} keys from active tracker")

    # Archive database (avoid re-discovering archived jobs)
    if NOTION_ARCHIVE_DB_ID:
        try:
            archive_pages = query_database(NOTION_ARCHIVE_DB_ID)
            archive_keys = _extract_keys_from_pages(archive_pages)
            dedup_keys.update(archive_keys)
            print(f"  Loaded {len(archive_keys)} keys from archive")
        except Exception as e:
            print(f"  Warning: Could not query archive DB: {e}")

    print(f"  Total dedup keys: {len(dedup_keys)}")
    return dedup_keys
