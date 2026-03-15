# Will's Job Tracker

Automated job discovery, scoring, review, and notification system. Scans 3 job board APIs daily, scores each role 0–10 against Will's profile, writes matches to Notion, archives stale listings, and sends email digests.

---

## How It Works

1. **6 AM ET** — GitHub Actions runs the discovery pipeline: fetches jobs from Adzuna, Remotive, and The Muse (with a JobSpy fallback if <5 new results), filters by location, deduplicates against active + archive databases, scores each job, and writes passing matches to Notion.
2. **Same run** — The review pipeline checks existing unacted-on jobs for dead links, past deadlines, age-based expiry, and non-US locations. Closed jobs are archived (copy → verify → delete).
3. **8 AM ET** — Daily email digest with new matches grouped by priority.
4. **9 AM ET** — Deadline reminder emails for jobs due within 3 days.
5. **Every 2 hrs (8AM–6PM ET)** — Interview prep: detects jobs moved to "Interview" status, generates tailored prep materials, creates NotebookLM notebook (audio overview + infographic), and emails Will.
6. **Mon 7 AM ET** — Monday kickoff coaching email with weekly stats and a rotating goal.
7. **Mon 7 AM ET** — Weekly summary email with new match and application counts.

---

## Scoring (0–10)

| Dimension | Weight | Best Score |
|-----------|--------|------------|
| Role type match (title vs description keywords) | 30% | 3.0 |
| Skills overlap with Will's profile | 20% | 2.0 |
| Work arrangement (Remote > Hybrid ATL > On-site) | 20% | 2.0 |
| Company size (small/medium preferred) | 10% | 1.0 |
| Industry (risk mgmt > finserv > general) | 10% | 1.0 |
| Seniority fit (mid-senior preferred) | 10% | 1.0 |

**Dealbreakers (force score to 0, never written to Notion):** All on-site jobs, travel required, 2+ toxic culture signals.

**Priority:** ≥7 High, ≥5 Medium, <5 Low.

---

## Repo Structure

```
Wills Job Search/
├── .github/workflows/
│   ├── job-pipeline.yml          # Daily: discovery → review → archive
│   ├── daily-digest.yml          # Daily: email new job matches
│   ├── weekly-summary.yml        # Monday: weekly rollup email
│   ├── deadline-reminder.yml     # Daily: deadline alert emails
│   └── interview-prep.yml       # Every 2hrs: interview prep automation
├── discovery/
│   ├── discover.py               # CLI: run | test-scoring
│   ├── config.py                 # Search params, weights, keywords
│   ├── scoring.py                # 0-10 scoring engine
│   ├── dedup.py                  # Title+company dedup (active + archive)
│   ├── location_filter.py        # Non-US / non-Latin rejection
│   ├── notion_writer.py          # Write scored jobs to Notion
│   ├── requirements.txt
│   └── sources/
│       ├── base.py               # RawJob dataclass, JobSource ABC
│       ├── adzuna.py              # Adzuna API
│       ├── remotive.py            # Remotive API
│       ├── themuse.py             # The Muse API
│       └── jobspy_source.py       # Indeed + Google Jobs fallback
├── review/
│   ├── review.py                 # CLI: run
│   ├── link_checker.py           # HTTP link verification
│   ├── archiver.py               # Copy-verify-delete to archive DB
│   └── requirements.txt
├── interview_prep/
│   ├── prep.py                   # CLI: run (detect Interview → generate prep → email)
│   ├── material_builder.py       # Scrape job desc, build company brief, generate questions
│   ├── notebooklm_client.py      # NotebookLM automation (audio, infographic, notebook)
│   └── requirements.txt
├── notifications/
│   ├── notify.py                 # CLI: daily-digest | weekly-summary | deadline-reminder
│   ├── requirements.txt
│   └── SETUP.md
├── notion_common.py              # Shared Notion API helpers
├── generate_resumes.py           # Resume generation (pre-pipeline)
└── STATUS.md                     # Detailed project status
```

---

## Notion Databases

| Database | Purpose |
|----------|---------|
| Active Job Tracker | All current jobs with 20+ properties (score, status, red flags, etc.) |
| Job Tracker Archive | Closed/expired/dismissed jobs with Date Archived and Close Reason |

---

## GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `NOTION_API_KEY` | Notion integration token |
| `NOTION_DATABASE_ID` | Active tracker database ID |
| `NOTION_ARCHIVE_DB_ID` | Archive database ID |
| `ADZUNA_API_ID` | Adzuna API app ID |
| `ADZUNA_API_KEY` | Adzuna API key |
| `GMAIL_ADDRESS` | Sender email for notifications |
| `GMAIL_APP_PASSWORD` | Gmail app password for SMTP |
| `NOTEBOOKLM_AUTH_JSON` | NotebookLM cookies for interview prep automation (optional) |

---

## Will's Profile

- 10+ years operations experience (Hiscox USA, AIG)
- U.S. Marine Corps veteran
- BBA in Risk Management and Insurance (Georgia State University)
- AINS designation
- AI certifications (2023–present)
- Target: Remote/hybrid operations, automation, data migration, business analysis, project management roles
