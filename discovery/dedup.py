"""
Deduplication logic.
Prevents the same job from being added to Notion twice.
Uses normalized title+company as the dedup key.
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import query_database, extract_property, NOTION_DATABASE_ID


def normalize(text):
    """Lowercase, strip whitespace, remove punctuation, collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def generate_dedup_key(title, company):
    """Create a deduplication key from title and company."""
    return f"{normalize(title)}|{normalize(company)}"


def load_existing_keys():
    """Fetch all jobs from Notion and return a set of dedup keys."""
    print("Loading existing jobs from Notion for deduplication...")
    all_pages = query_database(NOTION_DATABASE_ID)
    dedup_keys = set()
    for page in all_pages:
        title = extract_property(page, "Job Title")
        company = extract_property(page, "Company")
        if title or company:
            dedup_keys.add(generate_dedup_key(title, company))
    print(f"  Loaded {len(dedup_keys)} existing job keys")
    return dedup_keys
