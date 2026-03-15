# Will's Job Tracker — Project Status

Last updated: 2026-03-15

---

## What's Built and Live

### Job Discovery Pipeline (`discovery/`)

Scans 3 job board APIs daily, scores each job 0-10 against Will's profile, deduplicates against active tracker + archive, and writes passing jobs to Notion.

| Component | File | Status |
|-----------|------|--------|
| CLI entry point | `discovery/discover.py` | Live |
| Scoring engine (6 weighted dimensions) | `discovery/scoring.py` | Live |
| Dedup (active tracker + archive) | `discovery/dedup.py` | Live |
| Location filter (non-US/non-Latin rejection) | `discovery/location_filter.py` | Live |
| Notion writer | `discovery/notion_writer.py` | Live |
| Config (queries, weights, keywords) | `discovery/config.py` | Live |
| Adzuna API source | `discovery/sources/adzuna.py` | Live (requires API keys) |
| Remotive API source | `discovery/sources/remotive.py` | Live (no auth needed) |
| The Muse API source | `discovery/sources/themuse.py` | Live (no auth needed) |
| JobSpy fallback (Indeed + Google Jobs) | `discovery/sources/jobspy_source.py` | Live (triggers when <5 new jobs) |

**Pipeline flow:** Fetch from APIs → Location filter → Dedup → Score → Write to Notion

**Scoring dimensions:**
- Role type match (30%) — keywords in title vs description
- Skills match (20%) — overlap with Will's skills list
- Work arrangement (20%) — Remote/Hybrid/On-site with US location confidence penalty
- Company size (10%) — Small/Medium preferred
- Industry (10%) — Risk mgmt > FinServ > General
- Seniority (10%) — Mid-senior preferred

**Dealbreakers (force score to 0, never written to Notion):**
- All on-site jobs (regardless of location)
- Travel required
- 2+ toxic culture signals

---

### Job Status Review + Archive Pipeline (`review/`)

Checks existing unacted-on jobs for expiration and archives closed ones to a separate Notion database. Safety-first: never deletes without verified archive copy.

| Component | File | Status |
|-----------|------|--------|
| CLI entry point | `review/review.py` | Live |
| HTTP link checker | `review/link_checker.py` | Live |
| Copy-verify-delete archiver | `review/archiver.py` | Live |
| Archive DB creation script | `review/create_archive_db.py` | Created (used MCP instead) |

**Review checks (in priority order):**
1. **Dismissed** — Will marks `Dismissed = true` in Notion → archived with Dismissed Reason
2. **Non-Latin characters** — title/company with CJK/Cyrillic/Arabic → archived as "Non-US location"
3. **Link verification** — HTTP GET to Apply Link (404/410/closed indicators → "Link dead")
4. **Past deadline** — Apply By date is past → "Past deadline"
5. **Age-based expiry** — Date Found >30 days ago with no deadline → "Age-based expiry"

**Protected statuses (never auto-archived):** Applied, Interview, Offer, Rejected, Withdrawn
- Exception: Dismissed jobs are archived regardless of status

---

### Email Notifications (`notifications/`)

Python-based email system replacing Zapier. Sends formatted HTML emails via Gmail SMTP.

| Notification | Schedule | Status |
|-------------|----------|--------|
| Daily digest | 8 AM ET daily | Live (needs `GMAIL_APP_PASSWORD` secret) |
| Weekly summary | 7 AM ET Mondays | Live (needs `GMAIL_APP_PASSWORD` secret) |
| Deadline reminder | 9 AM ET daily | Live (needs `GMAIL_APP_PASSWORD` secret) |

---

### Shared Infrastructure

| Component | File | Status |
|-----------|------|--------|
| Shared Notion API helpers | `notion_common.py` | Live |
| Resume generator | `generate_resumes.py` | Exists (pre-pipeline) |

---

### GitHub Actions Workflows (`.github/workflows/`)

| Workflow | Schedule | Status |
|----------|----------|--------|
| `job-pipeline.yml` — Discovery + Review | 6 AM ET daily (11:00 UTC) | **Passing** |
| `daily-digest.yml` — Email digest | 8 AM ET daily (13:00 UTC) | Needs `GMAIL_APP_PASSWORD` |
| `weekly-summary.yml` — Weekly rollup | 7 AM ET Mondays (12:00 UTC Mon) | Needs `GMAIL_APP_PASSWORD` |
| `deadline-reminder.yml` — Deadline alerts | 9 AM ET daily (14:00 UTC) | Needs `GMAIL_APP_PASSWORD` |
| `interview-prep.yml` — Interview prep generator | Every 2 hrs, 8AM-6PM ET | Needs `GMAIL_APP_PASSWORD` + optional `NOTEBOOKLM_AUTH_JSON` |

---

### Notion Databases

| Database | ID | Status |
|----------|-----|--------|
| Active Job Tracker | `ac20106e-1c1c-4000-8065-f57850f48d10` | Live |
| Job Tracker Archive | `de8601cdd18d4258ac513c8415a3d11a` | Live |

**Active Tracker properties:** Job Title, Company, Match Score, Work Type, Employment Type, Salary Range, Company Intel, Apply Link, Priority, Red Flags (multi_select), Date Found, Status, Apply By, Applied, Company Rating, Source, Company Size, Industry, Dismissed, Dismissed Reason, NotebookLM Status, NotebookLM URLs

**Archive-specific properties:** Date Archived, Close Reason, Dismissed Reason

---

### GitHub Secrets Configured

| Secret | Status |
|--------|--------|
| `NOTION_API_KEY` | Configured |
| `NOTION_DATABASE_ID` | Configured |
| `NOTION_ARCHIVE_DB_ID` | Configured |
| `ADZUNA_API_ID` | Configured |
| `ADZUNA_API_KEY` | Configured |
| `CLAUDE_WILLS_JOB_TRACKER_API_KEY` | Configured (not used by pipeline) |
| `GMAIL_ADDRESS` | **Not configured** |
| `GMAIL_APP_PASSWORD` | **Not configured** |
| `NOTEBOOKLM_AUTH_JSON` | **Not configured** (optional — interview prep works without it) |

---

## What's Outstanding

### Blocking (prevents functionality)

| Item | Impact | Effort |
|------|--------|--------|
| Add `GMAIL_APP_PASSWORD` secret to GitHub | Email notifications won't send | 2 min |
| Add `GMAIL_ADDRESS` secret to GitHub | Email notifications won't send (has default fallback) | 2 min |

### Improvements

| Item | Description | Effort |
|------|-------------|--------|
| ~~Update README.md~~ | ~~Rewritten to match actual system~~ | Done |
| ~~Remove `github-workflows/` duplicate directory~~ | ~~Deleted; workflows are in `.github/workflows/`~~ | Done |
| Bump GitHub Actions versions | `actions/checkout@v4` → `v5`, `actions/setup-python@v5` → `v6` (Node.js 20 deprecation warning) | Small |
| Insurance industry scoring | Currently penalized at 0.2/1.0 — may want to adjust since Will has insurance background (Hiscox, AIG) | Small |
| Cowork resume tailoring workflow | On-demand resume/cover letter generation when Will chooses to apply | Medium |
| ~~NotebookLM interview prep automation~~ | ~~Built: `interview_prep/` module with NotebookLM integration, audio overview, infographic, fallback email~~ | Done |
| Company intelligence enrichment | Pull company size, culture, mission, AI initiatives beyond what job board APIs provide | Medium |
| Monday kickoff coaching email | Weekly email with stats, action items, and goals (beyond the current weekly summary) | Medium |

### Technical Debt

| Item | Description |
|------|-------------|
| ~~Duplicate `sys.path.insert` in `review/review.py`~~ | ~~Removed redundant line~~ |
| ~~Unused weighted_score in `scoring.py`~~ | ~~Removed dead code~~ |
| ~~`create_archive_db.py` not needed~~ | ~~Deleted~~ |

---

## Repo Structure

```
Wills Job Search/
├── .github/workflows/           # GitHub Actions (live)
│   ├── job-pipeline.yml         # Daily: discovery → review → archive
│   ├── daily-digest.yml         # Daily: email new job matches
│   ├── weekly-summary.yml       # Monday: weekly rollup email
│   └── deadline-reminder.yml    # Daily: deadline alert emails
├── discovery/                   # Job discovery pipeline
│   ├── discover.py              # CLI: run | test-scoring
│   ├── config.py                # Search params, weights, keywords
│   ├── scoring.py               # 0-10 scoring engine
│   ├── dedup.py                 # Title+company dedup (active + archive)
│   ├── location_filter.py       # Non-US / non-Latin rejection
│   ├── notion_writer.py         # Write scored jobs to Notion
│   ├── requirements.txt         # requests, python-jobspy
│   └── sources/
│       ├── base.py              # RawJob dataclass, JobSource ABC
│       ├── adzuna.py            # Adzuna API
│       ├── remotive.py          # Remotive API
│       ├── themuse.py           # The Muse API
│       └── jobspy_source.py     # Indeed + Google Jobs fallback
├── review/                      # Status review + archive pipeline
│   ├── review.py                # CLI: run
│   ├── link_checker.py          # HTTP link verification
│   ├── archiver.py              # Copy-verify-delete to archive DB
│   └── requirements.txt         # requests
├── notifications/               # Email notification system
│   ├── notify.py                # CLI: daily-digest | weekly-summary | deadline-reminder
│   ├── requirements.txt         # requests
│   └── SETUP.md                 # Setup guide
├── notion_common.py             # Shared Notion API helpers
├── generate_resumes.py          # Resume generation
├── Resumes/                     # Will's resumes (gitignored)
└── README.md                    # Needs update
```

---

## Daily Pipeline Execution Order

| Time (ET) | Workflow | What it does |
|-----------|----------|-------------|
| 6-7 AM | `job-pipeline.yml` | Discover new jobs → Review existing → Archive closed |
| 8-9 AM | `daily-digest.yml` | Email today's new matches (grouped by priority) |
| 9-10 AM | `deadline-reminder.yml` | Email jobs with deadlines in 3 days |
| Mon 7-8 AM | `weekly-summary.yml` | Weekly new match count + applied count rollup |
