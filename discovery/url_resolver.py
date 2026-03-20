"""
URL resolution and validation for job apply links.

Resolves aggregator redirect URLs (Adzuna, The Muse, etc.) to the actual
employer application page using a multi-strategy approach:
1. HTTP redirect following (handles 301/302 tracking redirects)
2. HTML parsing for apply/redirect links (handles JS/page-level redirects)
3. Validation and flagging for unresolvable aggregator URLs
"""

import re
import requests
from urllib.parse import urlparse

AGGREGATOR_DOMAINS = [
    "adzuna.com",
    "themuse.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "builtin.com",
    "linkedin.com/jobs",
    "jobgether.com",
    "remoterocketship.com",
    "remotive.com",
]

# User-Agent to avoid bot-detection blocks during redirect resolution
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Common employer ATS domains — if we find these in the page, they're very
# likely the real apply link even when mixed with other external URLs.
_ATS_DOMAINS = [
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "smartrecruiters.com",
    "icims.com",
    "jobvite.com",
    "ultipro.com",
    "breezy.hr",
    "bamboohr.com",
    "jazz.co",
    "applytojob.com",
    "recruitee.com",
    "personio.de",
    "taleo.net",
    "successfactors.com",
]


def is_aggregator_url(url):
    """Check if URL points to a job aggregator instead of the employer."""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in AGGREGATOR_DOMAINS)


def _is_search_page(url):
    """Detect generic search/listing pages with no specific job ID."""
    if not url:
        return False
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # BuiltIn-style generic listing pages: /jobs/remote/atlanta/operations
    if "builtin.com" in parsed.netloc:
        parts = [p for p in path.split("/") if p]
        if parts and parts[0] == "jobs" and len(parts) <= 4:
            return True

    # Glassdoor search pages (no specific job-listing ID)
    if "glassdoor.com" in parsed.netloc and "/job-listing/" not in path:
        return True

    return False


def _is_ats_url(url):
    """Check if URL points to a known ATS (applicant tracking system)."""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in _ATS_DOMAINS)


def _is_junk_url(url):
    """Filter out URLs that are obviously not job apply links."""
    if not url:
        return True
    low = url.lower()
    # Static assets, analytics, social, CDN
    junk_extensions = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                       ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map")
    junk_domains = ("google", "facebook", "twitter", "cloudflare", "cdn.",
                    "kxcdn.com", "googleapis.com", "gstatic.com", "fonts.",
                    "analytics", "doubleclick", "adservice", "sentry",
                    "hotjar", "segment", "newrelic", "datadoghq",
                    "cookiebot", "onetrust", "schema.org")
    if any(low.endswith(ext) for ext in junk_extensions):
        return True
    if any(d in low for d in junk_domains):
        return True
    return False


def _extract_employer_url_from_html(html, source_domain):
    """Parse HTML to find employer apply URLs.

    Scans the page content for links pointing to known ATS domains
    (Workday, Greenhouse, Lever, etc.). Only returns URLs that look like
    actual job application pages, filtering out static assets and analytics.
    """
    if not html:
        return None

    # Strategy 1: Look for known ATS URLs anywhere in the page
    # These are highly reliable — if Workday/Greenhouse/Lever URLs appear on
    # an aggregator page, they are almost certainly the employer apply link.
    ats_pattern = re.compile(
        r'(https?://[^\s"\'<>]*(?:' +
        "|".join(re.escape(d) for d in _ATS_DOMAINS) +
        r')[^\s"\'<>]*)',
        re.IGNORECASE,
    )
    for match in ats_pattern.finditer(html):
        url = match.group(1)
        if not _is_junk_url(url):
            return url

    # Strategy 2: Look for apply-context links (near "apply" text)
    # Match hrefs that appear near apply-related keywords
    apply_context = re.compile(
        r'(?:apply|application|submit|external.?link|view.?job|job.?posting)'
        r'[^>]{0,200}?'
        r'href\s*=\s*["\']'
        r'(https?://(?!' + re.escape(source_domain) + r')[^\s"\'<>]+)'
        r'["\']',
        re.IGNORECASE,
    )
    # Also check reverse: href first, then apply text nearby
    apply_context_rev = re.compile(
        r'href\s*=\s*["\']'
        r'(https?://(?!' + re.escape(source_domain) + r')[^\s"\'<>]+)'
        r'["\']'
        r'[^>]{0,200}?'
        r'(?:apply|application|submit|external.?link|view.?job|job.?posting)',
        re.IGNORECASE,
    )
    for pattern in (apply_context, apply_context_rev):
        for match in pattern.finditer(html):
            url = match.group(1)
            if not _is_junk_url(url) and not is_aggregator_url(url):
                return url

    return None


def resolve_url(url, timeout=10):
    """Resolve an aggregator URL to the employer's direct URL.

    Multi-strategy approach:
    1. Follow HTTP 301/302 redirects (handles tracking URLs)
    2. Parse the HTML response for employer URLs (handles JS/page redirects)
    3. Return original URL if nothing works

    Returns the resolved URL (may be the original if resolution fails).
    """
    if not url:
        return url

    source_domain = urlparse(url).netloc.lower()

    # Strategy 1: Try HEAD request for HTTP redirects (fast, no body download)
    try:
        resp = requests.head(
            url, allow_redirects=True, timeout=timeout, headers=_HEADERS
        )
        if resp.url != url and not is_aggregator_url(resp.url):
            return resp.url
    except requests.RequestException:
        pass

    # Strategy 2: GET request — follow redirects + parse body for employer URLs
    try:
        resp = requests.get(
            url, allow_redirects=True, timeout=timeout, headers=_HEADERS,
        )
        # Check if GET followed a redirect to a non-aggregator URL
        if resp.url != url and not is_aggregator_url(resp.url):
            return resp.url

        # Strategy 3: Parse page HTML for employer apply links
        if resp.status_code == 200:
            # Only read first 50KB to avoid downloading huge pages
            html = resp.text[:50_000]
            employer_url = _extract_employer_url_from_html(html, source_domain)
            if employer_url:
                return employer_url
    except requests.RequestException:
        pass

    return url


def resolve_apply_links(jobs):
    """Resolve apply links for all jobs that currently point to aggregators.

    Modifies jobs in-place. For each job whose apply_link is an aggregator URL:
    1. Follow redirects and parse page content for the employer's direct URL
    2. If the resolved URL is still an aggregator or a search page, flag it
       by setting job.notes

    Jobs with non-aggregator URLs are left untouched (no network call).
    Returns (resolved_count, flagged_count) for summary output.
    """
    resolved = 0
    flagged = 0

    for job in jobs:
        if not job.apply_link:
            continue

        original = job.apply_link

        # Only attempt resolution for aggregator URLs
        if not is_aggregator_url(original):
            continue

        final_url = resolve_url(original)

        if final_url != original:
            job.apply_link = final_url
            resolved += 1
            print(f"  [URL] Resolved: {_short(original)} → {_short(final_url)}")

        # Check if resolved URL is still an aggregator or a generic search page
        if is_aggregator_url(job.apply_link) or _is_search_page(job.apply_link):
            flagged += 1
            job.notes = "Apply Link may not be direct — verify before applying."
            print(f"  [URL] Flagged: {job.title} @ {job.company} — still aggregator/search page")

    return resolved, flagged


def _short(url, max_len=80):
    """Truncate a URL for log output."""
    return url if len(url) <= max_len else url[:max_len] + "..."
