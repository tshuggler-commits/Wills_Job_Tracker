"""
HTTP link verification for job listings.
Checks if Apply Link URLs are still active or expired.
"""

import re
import time
import requests

# Phrases indicating a job listing is closed
CLOSED_INDICATORS = [
    "this job is no longer available",
    "this position has been filled",
    "no longer accepting applications",
    "this listing has expired",
    "job not found",
    "this job has been removed",
    "this position is no longer available",
    "this role has been filled",
    "this opportunity is no longer available",
    "posting has expired",
    "job has expired",
    "position closed",
    "application closed",
]

# Domains that commonly redirect to generic pages when a listing expires
GENERIC_CAREER_PATHS = [
    "/careers", "/jobs", "/search", "/positions",
    "/job-search", "/career", "/openings",
]


def check_link(url, timeout=10):
    """
    Check if a job listing URL is still active.

    Returns:
        ("OPEN", None)         — job listing appears active
        ("CLOSED", reason)     — job listing is expired/removed
        ("INCONCLUSIVE", None) — couldn't determine (timeout, CAPTCHA, etc.)
    """
    if not url:
        return "INCONCLUSIVE", "No URL provided"

    try:
        resp = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        )
    except requests.Timeout:
        return "INCONCLUSIVE", "Request timed out"
    except requests.ConnectionError:
        return "INCONCLUSIVE", "Connection error"
    except requests.RequestException as e:
        return "INCONCLUSIVE", f"Request error: {e}"

    # Check HTTP status
    if resp.status_code == 404:
        return "CLOSED", "Link dead (404)"
    if resp.status_code == 410:
        return "CLOSED", "Link dead (410 Gone)"
    if resp.status_code == 429:
        # Rate limited — wait and retry once
        time.sleep(30)
        try:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code in (404, 410):
                return "CLOSED", f"Link dead ({resp.status_code})"
        except requests.RequestException:
            pass
        return "INCONCLUSIVE", "Rate limited (429)"
    if resp.status_code >= 400:
        return "INCONCLUSIVE", f"HTTP {resp.status_code}"

    # Check for redirect to generic careers page
    if resp.history:
        final_url = resp.url.lower()
        original_path = url.lower().split("?")[0]
        # If redirected to a different path that looks generic
        if final_url != original_path:
            for generic_path in GENERIC_CAREER_PATHS:
                if final_url.endswith(generic_path) or final_url.endswith(generic_path + "/"):
                    return "CLOSED", "Redirected to generic careers page"

    # Check page content for closed indicators
    try:
        content = resp.text.lower()[:50000]  # Only check first 50K chars
        for indicator in CLOSED_INDICATORS:
            if indicator in content:
                return "CLOSED", f"Page says: '{indicator}'"
    except Exception:
        pass

    # Check for common signs the page is just a CAPTCHA or login wall
    content_lower = resp.text.lower()[:10000] if resp.text else ""
    if "captcha" in content_lower or "verify you are human" in content_lower:
        return "INCONCLUSIVE", "CAPTCHA detected"
    if "sign in" in content_lower and "apply" not in content_lower:
        return "INCONCLUSIVE", "Login wall detected"

    # If we got a 200 with content, assume it's still open
    if resp.status_code == 200 and len(resp.text) > 500:
        return "OPEN", None

    return "INCONCLUSIVE", "Ambiguous response"
