"""
NotebookLM integration via notebooklm-py (unofficial library).

Handles authentication, notebook creation, source addition,
audio overview generation, infographic generation, and error handling.

Auth uses NOTEBOOKLM_AUTH_JSON env var containing the contents of
~/.notebooklm/storage_state.json (cookie-based, expires every ~2 weeks).
"""

import os
import json
import asyncio
import tempfile
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class NotebookLMResult:
    """Result of a notebook creation attempt."""
    success: bool
    notebook_url: str | None = None
    audio_generated: bool = False
    infographic_path: str | None = None
    error_message: str | None = None
    is_auth_error: bool = False


class AuthenticationError(Exception):
    """Raised when NotebookLM cookies are expired or invalid."""
    pass


# ---------------------------------------------------------------------------
# Auth setup
# ---------------------------------------------------------------------------

def _setup_auth():
    """
    Write NOTEBOOKLM_AUTH_JSON to a temp file for notebooklm-py.
    Returns the path to the temp storage_state.json file.
    """
    auth_json = os.environ.get("NOTEBOOKLM_AUTH_JSON", "").strip()
    if not auth_json:
        raise AuthenticationError("NOTEBOOKLM_AUTH_JSON environment variable not set")

    try:
        # Validate it's valid JSON
        json.loads(auth_json)
    except json.JSONDecodeError:
        raise AuthenticationError("NOTEBOOKLM_AUTH_JSON is not valid JSON")

    # Write to the expected location
    nlm_dir = os.path.expanduser("~/.notebooklm")
    os.makedirs(nlm_dir, exist_ok=True)
    storage_path = os.path.join(nlm_dir, "storage_state.json")

    with open(storage_path, "w") as f:
        f.write(auth_json)

    return storage_path


# ---------------------------------------------------------------------------
# Async notebook creation
# ---------------------------------------------------------------------------

async def _create_notebook_async(job, materials):
    """
    Create a NotebookLM notebook with interview prep sources.

    Steps:
    1. Create notebook
    2. Add 4 text sources (job desc, company research, questions, tips)
    3. Add Apply Link as URL source (if available)
    4. Generate audio overview
    5. Generate infographic
    6. Get share URL

    Returns NotebookLMResult.
    """
    try:
        from notebooklm import NotebookLMClient
    except ImportError:
        return NotebookLMResult(
            success=False,
            error_message="notebooklm-py not installed. Run: pip install notebooklm-py",
        )

    title = job.get("title", "Unknown Position")
    company = job.get("company", "Unknown Company")
    notebook_name = f"{company} \u2013 {title} Interview Prep"

    try:
        # Initialize client
        client = NotebookLMClient()

        # Step 1: Create notebook
        print(f"    Creating notebook: {notebook_name}")
        notebook = await client.create_notebook(title=notebook_name)
        notebook_id = notebook.id

        # Step 2: Add text sources
        sources = [
            ("Job Description", materials.job_description_text),
            ("Company Research", materials.company_research_text),
            ("Behavioral Questions", materials.behavioral_questions_text),
            ("Interview Strategy", materials.interview_tips_text),
        ]

        for source_name, source_text in sources:
            print(f"    Adding source: {source_name}")
            await client.add_source(
                notebook_id=notebook_id,
                content=source_text,
                title=source_name,
            )

        # Step 3: Add Apply Link as URL source (if available and scrape succeeded)
        apply_link = job.get("apply_link", "")
        if apply_link and materials.scrape_succeeded:
            try:
                print(f"    Adding URL source: {apply_link}")
                await client.add_url_source(
                    notebook_id=notebook_id,
                    url=apply_link,
                )
            except Exception as e:
                # Non-fatal — URL sources can fail for many reasons
                print(f"    URL source failed (non-fatal): {e}")

        # Step 4: Generate audio overview
        audio_generated = False
        try:
            print("    Generating audio overview...")
            await client.generate_audio_overview(notebook_id=notebook_id)
            audio_generated = True
            print("    Audio overview: generated")
        except Exception as e:
            print(f"    Audio overview failed (non-fatal): {e}")

        # Step 5: Generate infographic
        infographic_path = None
        try:
            print("    Generating infographic...")
            infographic = await client.generate_artifact(
                notebook_id=notebook_id,
                artifact_type="infographic",
            )
            # Download infographic to temp file
            if infographic:
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".png", prefix="interview_prep_", delete=False
                )
                tmp.write(infographic.content if hasattr(infographic, 'content') else b'')
                tmp.close()
                infographic_path = tmp.name
                print(f"    Infographic: saved to {infographic_path}")
        except Exception as e:
            print(f"    Infographic generation failed (non-fatal): {e}")

        # Step 6: Get share URL
        notebook_url = None
        try:
            share_info = await client.share_notebook(notebook_id=notebook_id)
            notebook_url = share_info.url if hasattr(share_info, 'url') else str(share_info)
            print(f"    Share URL: {notebook_url}")
        except Exception as e:
            # Try to construct URL from notebook_id
            notebook_url = f"https://notebooklm.google.com/notebook/{notebook_id}"
            print(f"    Share failed, using direct URL: {notebook_url}")

        return NotebookLMResult(
            success=True,
            notebook_url=notebook_url,
            audio_generated=audio_generated,
            infographic_path=infographic_path,
        )

    except Exception as e:
        error_str = str(e).lower()
        # Detect auth-related errors
        if any(kw in error_str for kw in [
            "auth", "login", "session", "cookie", "expired",
            "401", "403", "unauthenticated", "sign in",
        ]):
            return NotebookLMResult(
                success=False,
                is_auth_error=True,
                error_message=f"Authentication error: {e}",
            )

        return NotebookLMResult(
            success=False,
            error_message=str(e),
        )


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------

def create_interview_notebook(job, materials):
    """
    Synchronous entry point for notebook creation.
    Sets up auth and runs the async pipeline.
    Returns NotebookLMResult.
    """
    # Set up auth file from env var
    try:
        _setup_auth()
    except AuthenticationError as e:
        return NotebookLMResult(
            success=False,
            is_auth_error=True,
            error_message=str(e),
        )

    # Run async pipeline
    try:
        return asyncio.run(_create_notebook_async(job, materials))
    except Exception as e:
        return NotebookLMResult(
            success=False,
            error_message=f"Unexpected error: {e}",
        )
