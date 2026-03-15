"""
One-time script to create the Job Tracker Archive database in Notion.
Must be run before the review pipeline can archive jobs.

Usage:
    python -m review.create_archive_db

Requires:
    NOTION_TOKEN - Notion integration token

After running, add the printed database ID as NOTION_ARCHIVE_DB_ID
to your GitHub Secrets.
"""

import sys
import os
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import notion_headers, NOTION_API, NOTION_DATABASE_ID


def get_parent_page_id():
    """Get the parent page ID of the active Job Tracker database."""
    url = f"{NOTION_API}/databases/{NOTION_DATABASE_ID}"
    resp = requests.get(url, headers=notion_headers())
    resp.raise_for_status()
    data = resp.json()
    parent = data.get("parent", {})
    if parent.get("type") == "page_id":
        return parent["page_id"]
    elif parent.get("type") == "workspace":
        return None  # Top-level database
    return parent.get("page_id") or parent.get("block_id")


def create_archive_database(parent_page_id):
    """Create the Job Tracker Archive database with matching properties."""
    url = f"{NOTION_API}/databases"

    # Build parent reference
    if parent_page_id:
        parent = {"type": "page_id", "page_id": parent_page_id}
    else:
        parent = {"type": "page_id", "page_id": parent_page_id}

    properties = {
        # Title property (required)
        "Job Title": {"title": {}},

        # Core fields matching active tracker
        "Company": {"rich_text": {}},
        "Match Score": {"number": {"format": "number"}},
        "Salary Range": {"rich_text": {}},
        "Work Type": {
            "select": {
                "options": [
                    {"name": "Remote", "color": "green"},
                    {"name": "Hybrid", "color": "yellow"},
                    {"name": "On-site", "color": "red"},
                ]
            }
        },
        "Employment Type": {
            "select": {
                "options": [
                    {"name": "Full-time", "color": "blue"},
                    {"name": "Part-time", "color": "purple"},
                    {"name": "Contract", "color": "orange"},
                ]
            }
        },
        "Apply Link": {"url": {}},
        "Date Found": {"date": {}},
        "Source": {
            "select": {
                "options": [
                    {"name": "Adzuna", "color": "blue"},
                    {"name": "Remotive", "color": "green"},
                    {"name": "The Muse", "color": "purple"},
                    {"name": "Indeed", "color": "orange"},
                    {"name": "Google Jobs", "color": "yellow"},
                    {"name": "Manual", "color": "gray"},
                ]
            }
        },
        "Company Intel": {"rich_text": {}},
        "Red Flags": {"rich_text": {}},
        "Company Size": {
            "select": {
                "options": [
                    {"name": "Small", "color": "green"},
                    {"name": "Medium", "color": "yellow"},
                    {"name": "Large", "color": "red"},
                ]
            }
        },
        "Industry": {"select": {"options": []}},
        "Priority": {
            "select": {
                "options": [
                    {"name": "High", "color": "red"},
                    {"name": "Medium", "color": "yellow"},
                    {"name": "Low", "color": "green"},
                ]
            }
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "New", "color": "default"},
                    {"name": "Reviewing", "color": "blue"},
                    {"name": "Ready to Apply", "color": "yellow"},
                    {"name": "Applied", "color": "green"},
                    {"name": "Interviewing", "color": "purple"},
                    {"name": "Offer", "color": "green"},
                    {"name": "Rejected", "color": "red"},
                    {"name": "Withdrawn", "color": "gray"},
                    {"name": "Expired", "color": "gray"},
                ]
            }
        },
        "Apply By": {"date": {}},
        "Applied": {"checkbox": {}},
        "Company Rating": {"number": {"format": "number"}},

        # Archive-specific fields
        "Date Archived": {"date": {}},
        "Close Reason": {
            "select": {
                "options": [
                    {"name": "Link dead", "color": "red"},
                    {"name": "Past deadline", "color": "orange"},
                    {"name": "Age-based expiry", "color": "yellow"},
                ]
            }
        },
    }

    payload = {
        "parent": parent,
        "title": [{"type": "text", "text": {"content": "Job Tracker Archive"}}],
        "properties": properties,
    }

    resp = requests.post(url, headers=notion_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def main():
    from notion_common import NOTION_TOKEN
    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN environment variable not set")
        sys.exit(1)

    print("Looking up parent page of active Job Tracker...")
    parent_id = get_parent_page_id()
    if parent_id:
        print(f"  Parent page ID: {parent_id}")
    else:
        print("  Could not determine parent page. Database may be top-level.")
        print("  Please provide the parent page ID manually.")
        sys.exit(1)

    print("Creating Job Tracker Archive database...")
    result = create_archive_database(parent_id)

    archive_id = result.get("id", "")
    archive_url = result.get("url", "")

    print(f"\nArchive database created successfully!")
    print(f"  Database ID:  {archive_id}")
    print(f"  URL:          {archive_url}")
    print(f"\nNext step: Add this as NOTION_ARCHIVE_DB_ID to your GitHub Secrets:")
    print(f"  {archive_id}")


if __name__ == "__main__":
    main()
