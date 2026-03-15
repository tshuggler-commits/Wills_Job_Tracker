"""
Shared Notion API helpers used by notifications, discovery, and review modules.
"""

import os
import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "ac20106e-1c1c-4000-8065-f57850f48d10")
NOTION_ARCHIVE_DB_ID = os.environ.get("NOTION_ARCHIVE_DB_ID", "de8601cdd18d4258ac513c8415a3d11a")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def query_database(database_id, filter_obj=None, sorts=None):
    """Query a Notion database with optional filter. Returns all matching pages (handles pagination)."""
    url = f"{NOTION_API}/databases/{database_id}/query"
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    if sorts:
        payload["sorts"] = sorts

    all_results = []
    has_more = True
    start_cursor = None

    while has_more:
        if start_cursor:
            payload["start_cursor"] = start_cursor
        resp = requests.post(url, headers=notion_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return all_results


def extract_property(page, prop_name):
    """Extract a readable value from a Notion page property."""
    props = page.get("properties", {})
    prop = props.get(prop_name)
    if not prop:
        return ""

    prop_type = prop.get("type", "")

    if prop_type == "title":
        parts = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in parts)

    if prop_type == "rich_text":
        parts = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in parts)

    if prop_type == "number":
        val = prop.get("number")
        return val if val is not None else ""

    if prop_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""

    if prop_type == "multi_select":
        items = prop.get("multi_select", [])
        return ", ".join(item.get("name", "") for item in items)

    if prop_type == "url":
        return prop.get("url", "") or ""

    if prop_type == "checkbox":
        return prop.get("checkbox", False)

    if prop_type == "date":
        date_obj = prop.get("date")
        if date_obj:
            return date_obj.get("start", "")
        return ""

    if prop_type == "email":
        return prop.get("email", "") or ""

    return str(prop)


def extract_job(page):
    """Extract all job fields from a Notion page into a dict."""
    return {
        "title": extract_property(page, "Job Title"),
        "company": extract_property(page, "Company"),
        "match_score": extract_property(page, "Match Score"),
        "work_type": extract_property(page, "Work Type"),
        "employment_type": extract_property(page, "Employment Type"),
        "salary_range": extract_property(page, "Salary Range"),
        "company_intel": extract_property(page, "Company Intel"),
        "apply_link": extract_property(page, "Apply Link"),
        "priority": extract_property(page, "Priority"),
        "red_flags": extract_property(page, "Red Flags"),
        "date_found": extract_property(page, "Date Found"),
        "status": extract_property(page, "Status"),
        "apply_by": extract_property(page, "Apply By"),
        "applied": extract_property(page, "Applied"),
        "company_rating": extract_property(page, "Company Rating"),
        "notebooklm_status": extract_property(page, "NotebookLM Status"),
        "notebooklm_urls": extract_property(page, "NotebookLM URLs"),
        "page_id": page.get("id", ""),
        "page_url": page.get("url", ""),
    }


def create_page(database_id, properties):
    """Create a new page in a Notion database."""
    url = f"{NOTION_API}/pages"
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    resp = requests.post(url, headers=notion_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def update_page(page_id, properties):
    """Update properties on an existing Notion page."""
    url = f"{NOTION_API}/pages/{page_id}"
    payload = {"properties": properties}
    resp = requests.patch(url, headers=notion_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def archive_page(page_id):
    """Archive (soft-delete) a Notion page."""
    url = f"{NOTION_API}/pages/{page_id}"
    payload = {"archived": True}
    resp = requests.patch(url, headers=notion_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()
