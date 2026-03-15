"""
Interview Prep Pipeline — CLI entry point.

Detects jobs with Status="Interview" and generates prep materials,
creates a NotebookLM notebook (when auth is available), and emails Will.

Usage:
    python -m interview_prep.prep run

Environment variables required:
    NOTION_TOKEN           - Notion integration token
    NOTION_DATABASE_ID     - Active Job Tracker database ID
    GMAIL_ADDRESS          - Gmail address (sender and recipient)
    GMAIL_APP_PASSWORD     - Gmail app password
    NOTEBOOKLM_AUTH_JSON   - (Optional) NotebookLM auth for full automation
"""

import sys
import os
import time
import traceback

# Path setup — matches review/review.py pattern
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notifications"))

from notion_common import (
    query_database, extract_property, extract_job, update_page,
    NOTION_DATABASE_ID,
)
from notify import send_email, EMAIL_WRAPPER, TRACKER_URL
from .material_builder import build_prep_materials


# ---------------------------------------------------------------------------
# Notion queries
# ---------------------------------------------------------------------------

def _get_interview_jobs():
    """
    Query Notion for jobs where:
      - Status = "Interview"
      - NotebookLM Status is empty (not yet processed)
    """
    print("Querying Notion for Interview jobs needing prep...")

    filter_obj = {
        "and": [
            {"property": "Status", "select": {"equals": "Interview"}},
            {"property": "NotebookLM Status", "select": {"is_empty": True}},
        ]
    }

    pages = query_database(NOTION_DATABASE_ID, filter_obj=filter_obj)
    print(f"  Found {len(pages)} job(s) needing interview prep")
    return pages


# ---------------------------------------------------------------------------
# Notion update
# ---------------------------------------------------------------------------

def _update_notebooklm_status(page_id, status, urls=None):
    """Update NotebookLM Status and URLs on a Notion page."""
    properties = {
        "NotebookLM Status": {"select": {"name": status}},
    }
    if urls:
        properties["NotebookLM URLs"] = {
            "rich_text": [{"text": {"content": urls[:2000]}}]
        }
    try:
        update_page(page_id, properties)
        print(f"  Updated Notion: NotebookLM Status = '{status}'")
    except Exception as e:
        print(f"  Warning: Failed to update Notion: {e}")


# ---------------------------------------------------------------------------
# Email builders
# ---------------------------------------------------------------------------

def _build_prep_email_html(job, materials, notebook_url=None, infographic_path=None):
    """Build HTML email with interview prep summary."""
    title = job.get("title", "Unknown Position")
    company = job.get("company", "Unknown Company")
    score = job.get("match_score", "")
    work_type = job.get("work_type", "")
    apply_link = job.get("apply_link", "")

    content = f'''
    <div style="background: linear-gradient(135deg, #0a2e1f, #1a5c3a, #2d7a4f);
                padding: 32px 28px; border-radius: 12px 12px 0 0;">
        <h1 style="color: #fff; margin: 0 0 4px 0; font-size: 24px; font-weight: 700;">
            Interview Prep Ready
        </h1>
        <p style="color: #a8d5ba; margin: 0; font-size: 14px;">
            {title} at {company}
        </p>
    </div>

    <div style="padding: 24px 28px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background: #f0faf4; border: 1px solid #d4edda; border-radius: 8px; margin-bottom: 20px;">
            <tr>
                <td width="33%" align="center" style="padding: 16px 0;">
                    <div style="font-size: 24px; font-weight: 700; color: #2d7a4f;">
                        {score if score else "N/A"}
                    </div>
                    <div style="font-size: 11px; color: #888; text-transform: uppercase;">Match Score</div>
                </td>
                <td width="33%" align="center" style="padding: 16px 0;">
                    <div style="font-size: 16px; font-weight: 600; color: #333;">{work_type or "N/A"}</div>
                    <div style="font-size: 11px; color: #888; text-transform: uppercase;">Work Type</div>
                </td>
                <td width="33%" align="center" style="padding: 16px 0;">
                    <div style="font-size: 14px; color: #333;">
                        {"&#9989; Scraped" if materials.scrape_succeeded else "&#9888; From Tracker"}
                    </div>
                    <div style="font-size: 11px; color: #888; text-transform: uppercase;">Job Description</div>
                </td>
            </tr>
        </table>
    '''

    # NotebookLM link (if available)
    if notebook_url:
        content += f'''
        <div style="background: #eaf4fd; border: 1px solid #bee3f8; border-radius: 8px;
                    padding: 16px; margin-bottom: 20px; text-align: center;">
            <p style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: #1a5c3a;">
                Your NotebookLM prep is ready
            </p>
            <a href="{notebook_url}"
               style="display: inline-block; background: linear-gradient(135deg, #1a5c3a, #2d7a4f);
                      color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px;
                      font-size: 14px; font-weight: 600;">
                Open in NotebookLM &rarr;
            </a>
            <p style="margin: 12px 0 0 0; font-size: 12px; color: #888;">
                Includes audio overview, infographic, and all prep sources
            </p>
        </div>
        '''

    # Prep sections
    sections = [
        ("Company Research", materials.company_research_text),
        ("Behavioral Questions", materials.behavioral_questions_text),
        ("Interview Strategy", materials.interview_tips_text),
    ]

    for section_title, section_text in sections:
        # Convert markdown-style content to simple HTML
        html_text = section_text.replace("\n", "<br>")
        content += f'''
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 16px; color: #1a1a2e; margin: 0 0 4px 0; font-weight: 700;">
                {section_title}
            </h2>
            <div style="border-top: 2px solid #2d7a4f; padding-top: 12px; margin-top: 8px;">
                <div style="font-size: 13px; color: #333; line-height: 1.6;
                            max-height: 300px; overflow: hidden;">
                    {html_text[:3000]}
                </div>
            </div>
        </div>
        '''

    # Action buttons
    content += f'''
        <div style="text-align: center; margin-top: 24px; padding-top: 20px;
                    border-top: 1px solid #e8e6f0;">
    '''

    if apply_link:
        content += f'''
            <a href="{apply_link}"
               style="display: inline-block; background: #3498db; color: white;
                      padding: 10px 24px; text-decoration: none; border-radius: 8px;
                      font-size: 14px; font-weight: 600; margin: 0 8px;">
                View Job Posting
            </a>
        '''

    content += f'''
            <a href="{TRACKER_URL}"
               style="display: inline-block; background: #6366f1; color: white;
                      padding: 10px 24px; text-decoration: none; border-radius: 8px;
                      font-size: 14px; font-weight: 600; margin: 0 8px;">
                Open Tracker
            </a>
        </div>
    </div>
    '''

    return EMAIL_WRAPPER.format(content=content)


def _build_fallback_email_html(job, materials):
    """Build HTML email with full prep materials for manual NotebookLM upload."""
    title = job.get("title", "Unknown Position")
    company = job.get("company", "Unknown Company")

    content = f'''
    <div style="background: linear-gradient(135deg, #7a2d0a, #b84500);
                padding: 32px 28px; border-radius: 12px 12px 0 0;">
        <h1 style="color: #fff; margin: 0 0 4px 0; font-size: 24px; font-weight: 700;">
            Interview Prep (Manual Upload)
        </h1>
        <p style="color: #f5c6a8; margin: 0; font-size: 14px;">
            {title} at {company}
        </p>
    </div>

    <div style="padding: 24px 28px;">
        <div style="background: #fff5f5; border: 1px solid #fde8e8; border-radius: 8px;
                    padding: 16px; margin-bottom: 20px;">
            <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #c0392b;">
                &#9888; NotebookLM cookies expired
            </p>
            <p style="margin: 0; font-size: 13px; color: #666;">
                The prep materials are below — paste each section into NotebookLM as a text source.
                To restore automation:
            </p>
            <ol style="font-size: 13px; color: #666; margin: 8px 0 0 0; padding-left: 20px;">
                <li>Open Chrome, go to <a href="https://notebooklm.google.com">notebooklm.google.com</a>, sign in</li>
                <li>Run <code>pip install "notebooklm-py[browser]"</code> on your machine</li>
                <li>Run <code>notebooklm login</code> and complete sign-in</li>
                <li>Copy contents of <code>~/.notebooklm/storage_state.json</code></li>
                <li>Update the <code>NOTEBOOKLM_AUTH_JSON</code> secret in GitHub Settings &gt; Secrets</li>
            </ol>
        </div>

        <div style="background: #eaf4fd; border: 1px solid #bee3f8; border-radius: 8px;
                    padding: 16px; margin-bottom: 20px; text-align: center;">
            <a href="https://notebooklm.google.com"
               style="display: inline-block; background: #3498db; color: white;
                      padding: 10px 24px; text-decoration: none; border-radius: 8px;
                      font-size: 14px; font-weight: 600;">
                Open NotebookLM &rarr;
            </a>
        </div>
    '''

    # Full prep sections (formatted for easy copy-paste)
    sections = [
        ("Source 1: Job Description", materials.job_description_text),
        ("Source 2: Company Research", materials.company_research_text),
        ("Source 3: Behavioral Questions", materials.behavioral_questions_text),
        ("Source 4: Interview Strategy", materials.interview_tips_text),
    ]

    for section_title, section_text in sections:
        html_text = section_text.replace("\n", "<br>").replace("# ", "<strong>").replace("\n\n", "</strong><br><br>")
        content += f'''
        <div style="margin-bottom: 20px;">
            <h3 style="font-size: 14px; color: #1a1a2e; margin: 0 0 8px 0;
                       background: #f0f0f0; padding: 8px 12px; border-radius: 4px;">
                {section_title}
            </h3>
            <div style="font-size: 12px; color: #333; line-height: 1.5;
                        padding: 12px; background: #fafafa; border: 1px solid #e0e0e0;
                        border-radius: 4px; white-space: pre-wrap; font-family: monospace;">
                {html_text[:5000]}
            </div>
        </div>
        '''

    content += '''
        <p style="color: #888; font-size: 12px; text-align: center; margin-top: 20px;">
            Copy each section above into NotebookLM as a separate text source,
            then click "Generate Audio Overview" for a podcast-style prep session.
        </p>
    </div>
    '''

    return EMAIL_WRAPPER.format(content=content)


# ---------------------------------------------------------------------------
# Job processing
# ---------------------------------------------------------------------------

def _process_job(page):
    """
    Full pipeline for one job:
    1. Extract fields
    2. Build prep materials
    3. Try NotebookLM (if auth available)
    4. Update Notion
    5. Send email
    """
    job = extract_job(page)
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    page_id = job.get("page_id", "")
    label = f"{title} @ {company}"

    print(f"\nProcessing: {label}")

    # Step 1: Build prep materials
    print("  Building prep materials...")
    materials = build_prep_materials(job)
    print(f"  Job description: {'scraped from link' if materials.scrape_succeeded else 'from Notion fields'}")

    # Step 2: Try NotebookLM
    notebook_url = None
    infographic_path = None
    nlm_available = bool(os.environ.get("NOTEBOOKLM_AUTH_JSON", "").strip())

    if nlm_available:
        try:
            from .notebooklm_client import create_interview_notebook
            result = create_interview_notebook(job, materials)

            if result.success:
                notebook_url = result.notebook_url
                infographic_path = result.infographic_path
                print(f"  NotebookLM: notebook created ({notebook_url})")
                _update_notebooklm_status(page_id, "Sent", notebook_url)
            elif result.is_auth_error:
                print(f"  NotebookLM: auth expired — falling back to email-only")
                _update_notebooklm_status(page_id, "Failed - Manual")
            else:
                print(f"  NotebookLM: failed ({result.error_message}) — falling back to email-only")
                _update_notebooklm_status(page_id, "Failed - Manual")
        except ImportError:
            print("  NotebookLM: notebooklm-py not installed — email-only mode")
            _update_notebooklm_status(page_id, "Sent")
        except Exception as e:
            print(f"  NotebookLM: unexpected error — {e}")
            traceback.print_exc()
            _update_notebooklm_status(page_id, "Failed - Manual")
    else:
        print("  NotebookLM: NOTEBOOKLM_AUTH_JSON not set — email-only mode")
        _update_notebooklm_status(page_id, "Sent")

    # Step 3: Send email
    is_fallback = nlm_available and not notebook_url

    if is_fallback:
        subject = f"Interview Prep (Manual Upload): {title} @ {company}"
        html = _build_fallback_email_html(job, materials)
    else:
        subject = f"Interview Prep Ready: {title} @ {company}"
        html = _build_prep_email_html(job, materials, notebook_url, infographic_path)

    try:
        send_email(subject, html)
        print(f"  Email sent: {subject}")
    except Exception as e:
        print(f"  Warning: Failed to send email: {e}")

    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run():
    """Full interview prep pipeline."""
    print("=" * 60)
    print("INTERVIEW PREP GENERATOR")
    print("=" * 60)

    # Get jobs needing prep
    pages = _get_interview_jobs()

    if not pages:
        print("No jobs need interview prep. Done.")
        return

    # Check NotebookLM auth once (avoid per-job auth failures)
    nlm_auth = os.environ.get("NOTEBOOKLM_AUTH_JSON", "").strip()
    if nlm_auth:
        print("NotebookLM auth: configured (will attempt notebook creation)")
    else:
        print("NotebookLM auth: not configured (email-only mode)")

    # Process each job
    processed = 0
    errors = 0

    for i, page in enumerate(pages):
        title = extract_property(page, "Job Title")
        company = extract_property(page, "Company")
        print(f"\n[{i+1}/{len(pages)}] {title} @ {company}")

        try:
            _process_job(page)
            processed += 1
        except Exception as e:
            print(f"  Error processing job: {e}")
            traceback.print_exc()
            errors += 1

        # Rate limit between jobs
        if i < len(pages) - 1:
            time.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    print("INTERVIEW PREP SUMMARY")
    print("=" * 60)
    print(f"  Jobs processed:  {processed}")
    if errors:
        print(f"  Errors:          {errors}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    commands = {
        "run": run,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Usage: python -m interview_prep.prep <{'|'.join(commands.keys())}>")
        sys.exit(1)

    # Validate required env vars
    from notion_common import NOTION_TOKEN
    missing = []
    if not NOTION_TOKEN:
        missing.append("NOTION_TOKEN")
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    command = sys.argv[1]
    print(f"Running: {command}")
    commands[command]()
    print("Done.")


if __name__ == "__main__":
    main()
