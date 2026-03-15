# Will's Job Tracker

Automated job discovery, scoring, and notification system for Will's career search. Claude Code finds and scores jobs, Notion stores everything, and a notification layer (Google Apps Script + Zapier) keeps Will informed daily.

---

## How the System Works

Claude Code scans job boards overnight, scores each role against Will's profile, and pushes results into a Notion database. Every morning, Will gets an email digest ranking the best matches. On Mondays, a separate coaching email recaps the prior week and sets the week's priorities. When Will decides to apply, Cowork tailors his resume. When he lands an interview, NotebookLM preps him.

---

## System Architecture

| Layer | Tool | Purpose | Status |
|-------|------|---------|--------|
| Job Discovery + Scoring | Claude Code | Scan job boards, score against profile, populate Notion | Not built |
| Company Intelligence | Claude Code | Pull company size, culture, mission, AI initiatives, red flags | Not built |
| Central Database | Notion | Store all job data across 24 properties | Live |
| Daily Email Digest | Google Apps Script | Morning email with ranked unread jobs and priority matches | Live |
| Monday Kickoff Email | Google Apps Script | Weekly coaching email with stats, action items, and a goal | Not built |
| Deadline Reminders | Zapier | Email 3 days before Apply By date | Live |
| Interview Prep Alert | Zapier | Email when status changes to Interviewing | Live |
| Resume + Cover Letter | Cowork | On-demand tailoring from base resume | Not built |
| Interview Prep | NotebookLM | Audio overviews, flashcards, behavioral practice | Manual |

---

## Search Parameters

| Parameter | Value |
|-----------|-------|
| Role type | Operations, automation, data migration, business analysis, project management |
| Company size | Small to medium preferred |
| Work arrangement | Remote preferred, hybrid acceptable (Atlanta metro) |
| Relocation | No |
| Employment type | Full-time, part-time, and contract |
| Industry preference | Risk management space |
| Dealbreakers | Fully on-site, travel required, toxic leadership signals |

---

## Scoring Profile

The Claude Code pipeline scores each job against Will's background:

- 10+ years operations experience (Hiscox USA, AIG)
- U.S. Marine Corps veteran
- BBA in Risk Management and Insurance (Georgia State University)
- AINS designation
- AI certifications completed during career gap (2023 to present)
- 6 LinkedIn/Microsoft certifications

---

## Key IDs and Files

| Item | Value |
|------|-------|
| Notion database ID | `ac20106e-1c1c-4000-8065-f57850f48d10` |
| Notion data source ID | `5bd04902-6b54-4810-a15e-d9d995337adf` |
| Base resume | `WR-BASE-CURRENT.docx` |
| Resume naming convention | `WR-[Company]-[Role]-[Date]` |
| Daily digest script | Google Apps Script: `sendDailyDigest` |
| Monday kickoff script | Google Apps Script: `sendMondayKickoff` |

---

## Build Order

| Step | Task | Tool | Depends On |
|------|------|------|------------|
| 1 | Delete 3 OFF Zaps in Zapier | Zapier dashboard | Nothing |
| 2 | Build Monday Kickoff Email | Google Apps Script | Notion database |
| 3 | Build Claude Code job discovery pipeline | Claude Code | Notion database |
| 4 | Test full pipeline end to end | All tools | Steps 1 through 3 |
| 5 | Set up Cowork resume tailoring workflow | Cowork | Base resume |
| 6 | Document NotebookLM prep workflow | Markdown doc | Zap 2 |
| 7 | Automate NotebookLM uploads | notebooklm-mcp or notebooklm-py | Steps 4 through 6 |

---

## Secrets Required

This repo will need the following secrets configured in **Settings > Secrets and variables > Actions**:

| Secret | Purpose |
|--------|---------|
| `NOTION_API_KEY` | Authenticate with the Notion API to read/write job data |
| `ANTHROPIC_API_KEY` | Power the Claude Code scoring pipeline |

Additional secrets may be needed depending on which job board APIs the discovery pipeline integrates with.

---

## Repo Structure

```
wills-job-tracker/
├── README.md
├── .github/
│   └── workflows/        # GitHub Actions workflow files
├── scripts/
│   ├── discover.py       # Job board scanning and scoring
│   └── populate.py       # Push scored jobs to Notion
├── config/
│   └── search-params.json # Search parameters and scoring weights
└── docs/
    └── automation-plan.md # Full system documentation
```

> This structure will evolve as the pipeline gets built. The layout above is a starting point.

---

## Resources

- [Full Automation Plan](docs/automation-plan.md) for detailed specs on every component
- [Notion API docs](https://developers.notion.com/) for database integration reference
- [Anthropic API docs](https://docs.anthropic.com/) for Claude Code pipeline reference
