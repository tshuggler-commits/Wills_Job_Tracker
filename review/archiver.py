"""
Archive closed jobs: copy to archive DB, then delete from active tracker.
Safety-first: never delete without verified copy.
"""

import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import (
    create_page, archive_page, extract_property,
    NOTION_ARCHIVE_DB_ID,
)


def _build_archive_properties(page, close_reason):
    """Build properties dict for the archive database entry from an active tracker page."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Extract all properties from the original page
    def _text_prop(value):
        if not value:
            return None
        return {"rich_text": [{"text": {"content": str(value)[:2000]}}]}

    def _select_prop(value):
        if not value:
            return None
        return {"select": {"name": str(value)}}

    def _number_prop(value):
        if value == "" or value is None:
            return None
        try:
            return {"number": float(value)}
        except (ValueError, TypeError):
            return None

    def _url_prop(value):
        if not value:
            return None
        return {"url": str(value)}

    def _date_prop(value):
        if not value:
            return None
        return {"date": {"start": str(value)}}

    def _checkbox_prop(value):
        return {"checkbox": bool(value)}

    props = page.get("properties", {})

    # Map each field
    properties = {
        "Job Title": {"title": [{"text": {"content": extract_property(page, "Job Title") or "Untitled"}}]},
    }

    # Add optional fields only if they have values
    field_map = {
        "Company": _text_prop,
        "Salary Range": _text_prop,
        "Company Intel": _text_prop,
    }
    for field_name, builder in field_map.items():
        val = extract_property(page, field_name)
        if val:
            prop = builder(val)
            if prop:
                properties[field_name] = prop

    # Red Flags — copy as multi_select (preserve original format)
    red_flags_prop = props.get("Red Flags", {})
    if red_flags_prop.get("type") == "multi_select":
        items = red_flags_prop.get("multi_select", [])
        if items:
            properties["Red Flags"] = {"multi_select": [{"name": item["name"]} for item in items]}

    select_fields = [
        "Work Type", "Employment Type", "Source", "Company Size",
        "Industry", "Priority", "Status",
    ]
    for field_name in select_fields:
        val = extract_property(page, field_name)
        if val:
            prop = _select_prop(val)
            if prop:
                properties[field_name] = prop

    number_fields = ["Match Score", "Company Rating"]
    for field_name in number_fields:
        val = extract_property(page, field_name)
        if val != "":
            prop = _number_prop(val)
            if prop:
                properties[field_name] = prop

    url_val = extract_property(page, "Apply Link")
    if url_val:
        properties["Apply Link"] = _url_prop(url_val)

    date_fields = ["Date Found", "Apply By"]
    for field_name in date_fields:
        val = extract_property(page, field_name)
        if val:
            prop = _date_prop(val)
            if prop:
                properties[field_name] = prop

    applied_val = extract_property(page, "Applied")
    properties["Applied"] = _checkbox_prop(applied_val)

    # Archive-specific fields
    properties["Date Archived"] = {"date": {"start": today}}
    properties["Close Reason"] = {"select": {"name": close_reason}}

    return properties


def archive_job(page, close_reason):
    """
    Copy a job to the archive database, then delete from active tracker.

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    if not NOTION_ARCHIVE_DB_ID:
        return False, "NOTION_ARCHIVE_DB_ID not set"

    page_id = page.get("id", "")
    title = extract_property(page, "Job Title")
    company = extract_property(page, "Company")
    label = f"{title} @ {company}"

    # Step 1: Copy to archive
    try:
        properties = _build_archive_properties(page, close_reason)
        result = create_page(NOTION_ARCHIVE_DB_ID, properties)
        archive_id = result.get("id", "")
        if not archive_id:
            return False, f"Archive write returned no ID for {label}"
        print(f"  + Archived: {label} → {close_reason}")
    except Exception as e:
        return False, f"Failed to archive {label}: {e}"

    time.sleep(0.4)  # Rate limit

    # Step 2: Delete from active tracker (only after verified copy)
    try:
        archive_page(page_id)
        print(f"  - Removed from active: {label}")
    except Exception as e:
        # Archive succeeded but delete failed — log but don't return failure
        # The job is safely in the archive, just wasn't removed from active
        print(f"  ! Warning: Archived but failed to remove from active: {label}: {e}")

    time.sleep(0.4)  # Rate limit
    return True, None
