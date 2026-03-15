"""
Will's Job Tracker — Email Notification System

Replaces Zapier. Queries Notion API directly and sends formatted HTML emails via Gmail SMTP.

Usage:
    python notify.py daily-digest
    python notify.py weekly-summary
    python notify.py deadline-reminder

Environment variables required:
    NOTION_TOKEN          - Notion integration token (internal integration)
    NOTION_DATABASE_ID    - Job Tracker database ID
    GMAIL_ADDRESS         - Gmail address (sender and recipient)
    GMAIL_APP_PASSWORD    - Gmail app password (NOT your regular password)
"""

import os
import sys
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add parent directory to path so we can import notion_common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from notion_common import (
    query_database, extract_property, extract_job,
    NOTION_DATABASE_ID,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "wilsharp20@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
TRACKER_URL = "https://www.notion.so/ac20106e1c1c40008065f57850f48d10"


# ---------------------------------------------------------------------------
# Wrappers for backward-compatible query_database calls
# ---------------------------------------------------------------------------

def _query_database(filter_obj, sorts=None):
    """Wrapper that passes the active tracker database_id."""
    return query_database(NOTION_DATABASE_ID, filter_obj=filter_obj, sorts=sorts)


# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

def send_email(subject, html_body):
    """Send an HTML email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())

    print(f"Email sent: {subject}")


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

EMAIL_WRAPPER = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 700px; margin: 0 auto; padding: 20px; color: #1a1a1a;
             background-color: #ffffff;">
{content}
</body>
</html>
"""

PRIORITY_COLORS = {
    "High": {"bg": "#fef2f2", "border": "#dc2626", "text": "#991b1b", "badge": "#dc2626"},
    "Medium": {"bg": "#fffbeb", "border": "#d97706", "text": "#92400e", "badge": "#d97706"},
    "Low": {"bg": "#f0fdf4", "border": "#16a34a", "text": "#166534", "badge": "#16a34a"},
}


def format_score_bar(score):
    """Render a match score as a visual bar."""
    if not score and score != 0:
        return "N/A"
    score = float(score)
    filled = int(score)
    empty = 10 - filled
    color = "#dc2626" if score < 5 else "#d97706" if score < 7 else "#16a34a"
    bar = f'<span style="color:{color}; font-family: monospace;">{"&#9632;" * filled}{"&#9633;" * empty}</span>'
    return f'{bar} <strong>{score}/10</strong>'


def render_job_card(job):
    """Render a single job as an HTML card."""
    priority = job["priority"] or "Medium"
    colors = PRIORITY_COLORS.get(priority, PRIORITY_COLORS["Medium"])

    html = f'''
    <div style="margin-bottom: 16px; padding: 16px; border: 1px solid {colors["border"]};
                border-left: 4px solid {colors["border"]}; border-radius: 8px;
                background: {colors["bg"]};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <h3 style="margin: 0 0 6px 0; color: #111;">
                {job["title"] or "Untitled Position"}
            </h3>
        </div>
        <p style="margin: 0 0 10px 0; font-size: 15px; color: #444;">
            {job["company"] or "Unknown Company"}
        </p>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #333;">
            <tr>
                <td style="padding: 3px 12px 3px 0;"><strong>Match Score:</strong> {format_score_bar(job["match_score"])}</td>
                <td style="padding: 3px 12px 3px 0;"><strong>Work Type:</strong> {job["work_type"] or "N/A"}</td>
            </tr>
            <tr>
                <td style="padding: 3px 12px 3px 0;"><strong>Employment:</strong> {job["employment_type"] or "N/A"}</td>
                <td style="padding: 3px 12px 3px 0;"><strong>Salary:</strong> {job["salary_range"] or "Not listed"}</td>
            </tr>
        </table>
    '''

    if job["company_intel"]:
        intel_html = job["company_intel"].replace("\n", "<br>")
        html += f'''
        <div style="margin-top: 10px; padding: 10px; background: rgba(255,255,255,0.7);
                    border-left: 3px solid #6366f1; border-radius: 4px; font-size: 13px; color: #374151;">
            <strong>Company Intel:</strong><br>{intel_html}
        </div>
        '''

    if job["red_flags"]:
        html += f'''
        <p style="margin: 8px 0 0 0; color: #dc2626; font-size: 13px;">
            <strong>&#9888; Red Flags:</strong> {job["red_flags"]}
        </p>
        '''

    if job["apply_link"]:
        html += f'''
        <p style="margin: 10px 0 0 0;">
            <a href="{job["apply_link"]}" style="display: inline-block; padding: 6px 16px;
               background: {colors["badge"]}; color: white; text-decoration: none;
               border-radius: 4px; font-size: 13px; font-weight: 600;">Apply &rarr;</a>
        </p>
        '''

    if job["apply_by"]:
        html += f'''
        <p style="margin: 6px 0 0 0; font-size: 12px; color: #666;">
            <strong>Deadline:</strong> {job["apply_by"]}
        </p>
        '''

    html += "</div>"
    return html


# ---------------------------------------------------------------------------
# Notification: Daily Digest
# ---------------------------------------------------------------------------

def daily_digest():
    """
    Queries Notion for jobs where Date Found = today.
    Sends one email grouped by priority (High > Medium > Low).
    Sends nothing if no jobs found today.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Also compute "today" in ET for the subject line
    from datetime import timezone as tz
    et_offset = timedelta(hours=-5)  # EST; adjust to -4 for EDT if needed
    try:
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
        today_et = et_now.strftime("%Y-%m-%d")
        today_display = et_now.strftime("%B %-d, %Y")
    except Exception:
        today_et = today
        today_display = datetime.now().strftime("%B %d, %Y")

    print(f"Querying Notion for jobs found on {today_et}...")

    results = _query_database(
        filter_obj={
            "property": "Date Found",
            "date": {"equals": today_et}
        },
        sorts=[
            {"property": "Match Score", "direction": "descending"}
        ]
    )

    if not results:
        print("No new jobs found today. No email sent.")
        return

    jobs = [extract_job(page) for page in results]
    print(f"Found {len(jobs)} new job(s). Building email...")

    # Group by priority
    groups = {"High": [], "Medium": [], "Low": []}
    for job in jobs:
        p = job["priority"] if job["priority"] in groups else "Medium"
        groups[p].append(job)

    # Build HTML
    content = f'''
    <h1 style="margin: 0 0 4px 0; color: #111; font-size: 24px;">
        Will's Job Digest
    </h1>
    <p style="margin: 0 0 20px 0; color: #666; font-size: 14px;">
        {today_display} &mdash; {len(jobs)} new match{"es" if len(jobs) != 1 else ""}
    </p>
    '''

    for level in ["High", "Medium", "Low"]:
        if not groups[level]:
            continue
        colors = PRIORITY_COLORS[level]
        content += f'''
        <h2 style="color: {colors["text"]}; border-bottom: 2px solid {colors["border"]};
                   padding-bottom: 6px; margin-top: 28px; font-size: 18px;">
            {level} Priority ({len(groups[level])})
        </h2>
        '''
        for job in groups[level]:
            content += render_job_card(job)

    content += f'''
    <hr style="margin-top: 32px; border: none; border-top: 1px solid #e5e7eb;">
    <p style="color: #666; font-size: 13px; margin-top: 12px;">
        <strong>Deadlines this week:</strong>
        <a href="{TRACKER_URL}" style="color: #4f46e5;">Check your tracker</a>
    </p>
    '''

    subject = f"Will's Job Digest \u2014 {today_display} ({len(jobs)} new match{'es' if len(jobs) != 1 else ''})"
    send_email(subject, EMAIL_WRAPPER.format(content=content))


# ---------------------------------------------------------------------------
# Notification: Weekly Summary
# ---------------------------------------------------------------------------

def weekly_summary():
    """
    Queries Notion for:
      1. Jobs found in the past 7 days (count)
      2. Jobs with Status = Applied (total count)
    Sends a short Monday morning rollup.
    """
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
        today_display = now_et.strftime("%B %-d, %Y")
    except Exception:
        today_display = datetime.now().strftime("%B %d, %Y")

    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    print("Querying Notion for this week's matches...")
    new_matches = _query_database(
        filter_obj={
            "property": "Date Found",
            "date": {"on_or_after": seven_days_ago}
        }
    )

    print("Querying Notion for applied jobs...")
    applied_jobs = _query_database(
        filter_obj={
            "property": "Status",
            "select": {"equals": "Applied"}
        }
    )

    new_count = len(new_matches)
    applied_count = len(applied_jobs)

    # Count by priority for the new matches
    priority_breakdown = {"High": 0, "Medium": 0, "Low": 0}
    for page in new_matches:
        p = extract_property(page, "Priority")
        if p in priority_breakdown:
            priority_breakdown[p] += 1
        else:
            priority_breakdown["Medium"] += 1

    print(f"New matches: {new_count}, Applied: {applied_count}")

    content = f'''
    <h1 style="margin: 0 0 4px 0; color: #111; font-size: 24px;">
        Weekly Job Search Summary
    </h1>
    <p style="margin: 0 0 24px 0; color: #666; font-size: 14px;">
        Week ending {today_display}
    </p>

    <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
        <tr>
            <td style="padding: 20px; text-align: center; background: #eff6ff;
                       border-radius: 8px 0 0 8px; border: 1px solid #dbeafe;">
                <div style="font-size: 36px; font-weight: 700; color: #1d4ed8;">{new_count}</div>
                <div style="font-size: 13px; color: #64748b; margin-top: 4px;">New Matches</div>
            </td>
            <td style="width: 12px;"></td>
            <td style="padding: 20px; text-align: center; background: #f0fdf4;
                       border-radius: 0 8px 8px 0; border: 1px solid #bbf7d0;">
                <div style="font-size: 36px; font-weight: 700; color: #16a34a;">{applied_count}</div>
                <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Applications Sent</div>
            </td>
        </tr>
    </table>
    '''

    if new_count > 0:
        content += '''
        <h3 style="margin: 0 0 8px 0; color: #374151; font-size: 15px;">This Week's Matches by Priority</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 24px;">
        '''
        for level, count in priority_breakdown.items():
            if count == 0:
                continue
            colors = PRIORITY_COLORS[level]
            content += f'''
            <tr>
                <td style="padding: 6px 0;">
                    <span style="display: inline-block; padding: 2px 10px; background: {colors["badge"]};
                                 color: white; border-radius: 12px; font-size: 12px; font-weight: 600;">
                        {level}
                    </span>
                </td>
                <td style="padding: 6px 0; font-weight: 600;">{count}</td>
            </tr>
            '''
        content += "</table>"

    content += f'''
    <div style="padding: 14px; background: #fffbeb; border: 1px solid #fde68a;
                border-radius: 8px; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 14px; color: #92400e;">
            <strong>&#128197; Reminder:</strong> Review your
            <a href="{TRACKER_URL}" style="color: #b45309; font-weight: 600;">
                "This Week's Deadlines" view in Notion
            </a>
            before Friday.
        </p>
    </div>

    <hr style="margin-top: 24px; border: none; border-top: 1px solid #e5e7eb;">
    <p style="color: #666; font-size: 13px; margin-top: 12px;">
        <a href="{TRACKER_URL}" style="color: #4f46e5;">Open Job Tracker</a>
    </p>
    '''

    subject = f"Will's Weekly Job Search Summary \u2014 {new_count} new, {applied_count} applied"
    send_email(subject, EMAIL_WRAPPER.format(content=content))


# ---------------------------------------------------------------------------
# Notification: Deadline Reminder
# ---------------------------------------------------------------------------

def deadline_reminder():
    """
    Queries Notion for jobs where:
      - Apply By date is exactly 3 days from now
      - Applied checkbox is NOT checked
    Sends a reminder email for each upcoming deadline.
    """
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
        three_days = (now_et + timedelta(days=3)).strftime("%Y-%m-%d")
        today_display = now_et.strftime("%B %-d, %Y")
    except Exception:
        three_days = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        today_display = datetime.now().strftime("%B %d, %Y")

    print(f"Querying Notion for deadlines on {three_days}...")

    results = _query_database(
        filter_obj={
            "and": [
                {
                    "property": "Apply By",
                    "date": {"equals": three_days}
                },
                {
                    "property": "Applied",
                    "checkbox": {"equals": False}
                }
            ]
        },
        sorts=[
            {"property": "Priority", "direction": "ascending"},
            {"property": "Match Score", "direction": "descending"}
        ]
    )

    if not results:
        print("No upcoming deadlines in 3 days. No email sent.")
        return

    jobs = [extract_job(page) for page in results]
    print(f"Found {len(jobs)} upcoming deadline(s). Building email...")

    content = f'''
    <h1 style="margin: 0 0 4px 0; color: #dc2626; font-size: 24px;">
        &#9888; Deadline Reminder
    </h1>
    <p style="margin: 0 0 20px 0; color: #666; font-size: 14px;">
        {len(jobs)} application{"s" if len(jobs) != 1 else ""} due in 3 days ({three_days})
    </p>
    '''

    for job in jobs:
        content += render_job_card(job)

    content += f'''
    <div style="padding: 14px; background: #fef2f2; border: 1px solid #fecaca;
                border-radius: 8px; margin: 20px 0;">
        <p style="margin: 0; font-size: 14px; color: #991b1b;">
            <strong>Action needed:</strong> Review these jobs and apply before {three_days},
            or update their status in
            <a href="{TRACKER_URL}" style="color: #dc2626; font-weight: 600;">Notion</a>.
        </p>
    </div>

    <hr style="margin-top: 24px; border: none; border-top: 1px solid #e5e7eb;">
    <p style="color: #666; font-size: 13px; margin-top: 12px;">
        <a href="{TRACKER_URL}" style="color: #4f46e5;">Open Job Tracker</a>
    </p>
    '''

    subject = f"&#9888; {len(jobs)} application deadline{'s' if len(jobs) != 1 else ''} in 3 days"
    send_email(subject, EMAIL_WRAPPER.format(content=content))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

COMMANDS = {
    "daily-digest": daily_digest,
    "weekly-summary": weekly_summary,
    "deadline-reminder": deadline_reminder,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python notify.py <{'|'.join(COMMANDS.keys())}>")
        sys.exit(1)

    # Validate required env vars
    missing = []
    from notion_common import NOTION_TOKEN
    if not NOTION_TOKEN:
        missing.append("NOTION_TOKEN")
    if not GMAIL_APP_PASSWORD:
        missing.append("GMAIL_APP_PASSWORD")
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Set these as GitHub Actions secrets or export them locally.")
        sys.exit(1)

    command = sys.argv[1]
    print(f"Running: {command}")
    COMMANDS[command]()
    print("Done.")


if __name__ == "__main__":
    main()
