# Automation Plan Changelog

All design decisions made after the original wills-job-tracker-automation-plan.md was written. Read the original plan first, then this doc for everything that changed. When the two conflict, this doc wins.

---

## Blockers (Fix Now)

Issues actively breaking the system. Resolve these before any new build work.

### 1. Daily Digest email failing (GitHub Actions)

The daily-digest.yml workflow is failing with exit code 1. Will is not receiving his morning email.

| Detail | Value |
|--------|-------|
| Root cause | Gmail app password missing from GitHub Secrets |
| Where to fix | GitHub repo → Settings → Secrets and variables → Actions → New repository secret |
| Secret name | Check daily-digest.yml for the exact env var name (likely `EMAIL_PASSWORD` or `GMAIL_APP_PASSWORD`) |
| Secret value | A Gmail App Password (not Will's regular password) |
| How to generate | myaccount.google.com → Security → 2-Step Verification → App passwords → Create for "Mail" → Copy the 16-character code |
| After fixing | Go to Actions tab → click the failed run → "Re-run all jobs" |

- [ ] Add Gmail app password to GitHub Secrets → GitHub repo → Settings → Secrets and variables → Actions

### 2. Node.js 20 deprecation warning (GitHub Actions)

Not breaking yet, but will break after June 2, 2026. Both `actions/checkout@v4` and `actions/setup-python@v5` need updating.

| Detail | Value |
|--------|-------|
| Where to fix | All .yml files in `.github/workflows/` in the Claude Code repo |
| What to change | Update `actions/checkout@v4` to `@v5` and `actions/setup-python@v5` to `@v6` (or whatever versions support Node.js 24) |
| Deadline | June 2, 2026 |

- [ ] Update GitHub Actions to Node.js 24 compatible versions → `.github/workflows/daily-digest.yml` and `.github/workflows/interview-prep.yml`

---

## Quick Reference: Files, IDs, and Locations

Everything you need to find anything in this system.

### Notion

| Item | ID |
|------|----|
| Job Tracker database | `ac20106e-1c1c-4000-8065-f57850f48d10` |
| Data source ID | `5bd04902-6b54-4810-a15e-d9d995337adf` |
| Total properties | 47 |

### GitHub Repos and Scripts

| Item | Location |
|------|----------|
| Claude Code pipeline (discovery + scoring + interview prep) | GitHub repo, `discovery/` and `interview_prep/` directories |
| Daily digest workflow | `.github/workflows/daily-digest.yml` |
| Interview prep workflow | `.github/workflows/interview-prep.yml` |
| Scoring (on-site dealbreaker lives here) | `discovery/scoring.py` |
| Location filter | `discovery/location_filter.py` (also in project knowledge: `location_filter.py`) |
| Notion writer | `discovery/discover.py` |
| Interview prep orchestrator | `interview_prep/prep.py` |
| Interview materials builder | `interview_prep/material_builder.py` |
| NotebookLM client | `interview_prep/notebooklm_client.py` |

### Google Apps Script

| Item | Location |
|------|----------|
| Daily digest | Apps Script project "Will's Job Digest" → function `sendDailyDigest` |
| Monday kickoff (not yet built) | Same project → function `sendMondayKickoff` |
| Monday kickoff spec script | Project knowledge: `sendMondayKickoff.js` |

### Zapier

| Zap | Status |
|-----|--------|
| Zap 2: Interview Prep Alert | Active |
| Zap 4: Deadline Reminders | Active |
| Daily Job Digest, Zap 1, Weekly Digest | OFF, need deleting (Step 1) |

### Dashboard Prototype

| Item | Location |
|------|----------|
| Current prototype | `dashboard-v5-clean.jsx` (project knowledge + outputs) |
| Previous iterations | v1 through v4 in outputs (superseded) |

### Key Files

| File | What it is |
|------|-----------|
| `wills-job-tracker-automation-plan.md` | Original automation plan (project knowledge) |
| `automation-plan-changelog.md` | This document |
| `dismiss-archive-implementation-guide.md` | Dismiss/archive flow spec (project knowledge) |
| `WR-BASE-CURRENT.docx` | Will's base resume for Cowork tailoring |
| `wills-job-tracker-prompt.md` | Context prompt for Claude Code sessions |
| `wills-job-tracker-project-summary.md` | Project summary for session continuity |

### Credentials and Secrets Needed

| Secret | Where it goes | Status |
|--------|--------------|--------|
| Gmail App Password | GitHub repo → Settings → Secrets → Actions | MISSING (blocker) |
| `NOTEBOOKLM_AUTH_JSON` | GitHub repo → Settings → Secrets → Actions | Optional (system falls back to email-only prep) |
| Notion API Key | GitHub Secrets + Vercel env vars (when dashboard is built) | In GitHub, not yet in Vercel |
| `NEXTAUTH_SECRET` | Vercel env vars (when dashboard is built) | Not yet created |
| Tanya + Will login credentials | Vercel env vars (when dashboard is built) | Not yet created |

---

## New Layer: Vercel Dashboard

The biggest change. The original plan had no interactive frontend. Will's primary interface was email (daily digest + Monday kickoff) with Notion as the database he'd occasionally open.

**What changed:** We designed and prototyped a custom dashboard hosted on Vercel (Next.js, App Router) that becomes Will's daily command center. The dashboard reads from and writes to Notion through server-side API routes. Notion stays the source of truth. The dashboard is the interaction layer.

**Why:** Email is read-only. Will can't dismiss a job, mark it applied, or review a resume from an email. He had to context-switch to Notion and navigate 24+ fields. The dashboard gives him a purpose-built interface where every action is one or two taps.

| Detail | Value |
|--------|-------|
| Hosting | Vercel free tier |
| Framework | Next.js (App Router) with server components |
| Styling | Tailwind CSS |
| Auth | NextAuth with credentials provider, two accounts (Tanya + Will) |
| Database | Notion (existing). No new database. |
| Design priority | Mobile-first. Job searching happens on phones. |

**Dashboard structure:**

| Tab | Purpose |
|-----|---------|
| Review | Will's daily workflow. Score-sorted job cards with bookmark/dismiss actions. Monday banner on Mondays. |
| Pipeline | Will's active jobs grouped by stage: Pursuing, Applied, Interviewing. Each card shows what needs to happen next. |

The original plan's "Build Order" section has no mention of the dashboard. It needs to be added as a major build item between the pipeline and Cowork setup.

---

## Cowork: From On-Demand to Auto-Triggered

**Original plan said:** "This is on-demand, not automated. Will reviews his daily digest, picks a job he wants to apply to, and triggers Cowork to tailor his materials."

**What changed:** Resume tailoring now triggers automatically when Will bookmarks a job in the dashboard or checks a "Pursue" checkbox in Notion. Both actions write to the same Notion property. Cowork picks up the change and generates the tailored resume without Will doing anything.

### The resume flow

| Step | What happens | Where Will sees it |
|------|-------------|-------------------|
| 1. Will bookmarks a job | Dashboard writes `Bookmarked = true` to Notion | Toast: "Added to shortlist, tailoring resume" |
| 2. Cowork generates resume | Reads base resume + job details from Notion, writes tailored version | Pipeline card shows "Tailoring resume..." with spinner |
| 3. Resume ready | Cowork writes tailored content back to Notion | Pipeline card shows "Resume ready for review" |
| 4. Will reviews inline | Dashboard shows tailored summary, skills emphasized, and experience framing | Tap "Review" to expand, then Approve or Edit Full Doc |
| 5. Will approves | Dashboard writes `Resume Status = approved` to Notion | Card shows Apply button with direct link to company posting |

### Mapping to existing Notion fields

The database already has a `Resume Review Status` select with options that map cleanly to the dashboard flow:

| Dashboard State | Notion `Resume Review Status` Value |
|----------------|-------------------------------------|
| "Tailoring resume..." | Not Started (Cowork hasn't finished) |
| "Resume ready for review" | AI Draft Ready |
| Will is reviewing | Under Review |
| Will approved | Approved |
| Will requested changes | Needs Revision |

No new `Resume Status` property needed. The dashboard reads `Resume Review Status` directly. Cowork writes "AI Draft Ready" when it finishes generating, and the dashboard writes "Approved" when Will taps Approve.

**Tailored Summary**, **Skills Emphasized**, and **Experience Framing** are the three new fields Cowork populates for the inline review.

### New Notion properties needed for this flow

| Property | Type | Values |
|----------|------|--------|
| Bookmarked | Checkbox | true/false (triggers Cowork) |
| Tailored Summary | Rich Text | The rewritten summary statement |
| Skills Emphasized | Rich Text | Comma-separated list of skills Cowork pulled forward |
| Experience Framing | Rich Text | How Cowork repositioned Will's background |

The resume version naming convention (`WR-[Company]-[Role]-[Date]`) stays for file management but is never shown to Will in the dashboard. It's a system-level identifier.

---

## Cover Letter: Unresolved Gap

The original plan mentions cover letters alongside resumes: "Generate a tailored resume version... Generate a matching cover letter."

The dashboard only handles resumes. Cover letters have no tracking, no inline review, and no status field. This needs a decision.

**Options to resolve:**

| Option | Tradeoff |
|--------|----------|
| Bundle cover letter into the same review flow | More content for Will to review inline, but keeps everything in one place |
| Generate cover letter as a separate file, link it from the card | Less clutter in the review, but Will has to open a separate doc |
| Skip cover letters entirely unless the posting requires one | Simplest. Many roles don't ask for one. Flag it as a field on the job record. |

- [ ] Decision needed: How to handle cover letters in the dashboard.

---

## Emails: From Primary Interface to Notification Layer

**Original plan said:** The daily digest and Monday kickoff email were Will's main touchpoints with the system. The digest was the place he reviewed jobs. The kickoff was his weekly coaching moment.

**What changed:** The dashboard replaces both as Will's primary interface. Emails become a lightweight notification that says "things need your attention, open the dashboard."

### Current state of each email

| Email | Original Role | New Role | Status |
|-------|--------------|----------|--------|
| Daily Digest | Full job review interface with cards, scores, actions | Lightweight alert: "3 new matches, 1 deadline this week. [Open Dashboard]" | Needs rewrite |
| Monday Kickoff | Coaching email with stats, goals, action items | Lives in dashboard banner. Email version TBD. | Not built. Dashboard banner is the prototype. |
| Deadline Reminders (Zap 4) | Individual emails per upcoming deadline | Keep as-is. These are time-sensitive alerts that work well as push emails. | No change |
| Interview Prep Alert (Zap 2) | Email when status changes to Interviewing | Keep as-is. Add dashboard link. | Minor update |

We deferred the full notification strategy. The plan is: let Will use the dashboard for a week, then decide whether emails should be slimmed down, replaced, or supplemented with browser push notifications from the Vercel app.

---

## On-Site Jobs: Hard Dealbreaker (COMPLETED)

**Original plan said:** On-site was listed as a dealbreaker in Will's search parameters, but the scoring spec treated it as a penalty (lower score) rather than a filter (score 0, never written to Notion).

**What changed:** Three layers now block on-site jobs.

| Layer | File | What it does | Status |
|-------|------|-------------|--------|
| Scoring | `discovery/scoring.py` | `workType === "On-site"` sets score to 0 | Built |
| Notion writer | `discovery/discover.py` | Zero-score jobs logged but never written to Notion | Built |
| Dashboard safety net | Vercel app (frontend filter) | `jobs.filter(j => j.workType !== "On-site")` drops any that slip through | In prototype |

The "Add Job" form in the dashboard only offers Remote and Hybrid as work type options. On-site is not a choice.

---

## Pipeline: Score Removed From Post-Decision Views

The match score (the number in the colored block) only appears in the Review tab where Will is evaluating new jobs. Once a job moves to the Pipeline (Pursuing, Applied, Interviewing), the score is removed from the card.

**Why:** The score's purpose is to help Will decide whether to pursue a job. After he's made that decision, the number adds no value. Pipeline cards show what matters at each stage instead: resume status for Pursuing, days since application for Applied, interview countdown for Interviewing.

---

## Interview Lifecycle: New Feature (Partially Built)

The original plan had one status: "Interviewing." The dashboard needs to support the full interview lifecycle because Will can't track rounds, notes, contacts, or next steps.

### Interview Prep Materials Engine (COMPLETED)

The backend is built. `interview_prep/prep.py` orchestrates the full flow:

| Component | File | What it does | Status |
|-----------|------|-------------|--------|
| Orchestrator | `interview_prep/prep.py` | Queries Notion for `Status="Interview" AND NotebookLM Status is_empty`, processes each job, sends prep email, updates Notion | Built |
| Materials builder | `interview_prep/material_builder.py` | Generates 4 structured documents per job | Built |
| NotebookLM client | `interview_prep/notebooklm_client.py` | Wraps notebooklm-py with cookie auth, creates notebook, adds sources, generates audio overview + infographic | Built |
| Deployment | `.github/workflows/interview-prep.yml` | Runs every 2 hours during business hours (8AM-6PM ET). Manual trigger available. | Built |

**The 4 prep documents generated per job:**

1. **Job Description** — scraped from Apply Link via BeautifulSoup, falls back to Notion fields
2. **Company Research Brief** — assembled from Company Intel, Size, Industry, Red Flags
3. **Behavioral Questions** — bank of ~50 questions across 10 categories, keyword-matched to select 10-15 most relevant, each with STAR hints referencing Will's experience
4. **Interview Strategy Guide** — with competitive advantages, dynamic talking points, red flag probing questions, remote interview tips

**NotebookLM integration:** Creates a notebook with 4 text sources + the Apply Link URL, generates an audio overview and infographic. Falls back to email-only prep if NotebookLM auth expires (`NOTEBOOKLM_AUTH_JSON` GitHub Secret is optional).

### Dashboard Interview UI (NOT YET BUILT)

The prep engine runs automatically. But the dashboard has no way for Will to see prep materials, track multiple rounds, or log notes. That's the remaining work.

**New Notion properties for interview tracking:**

| Property | Type | Purpose |
|----------|------|---------|
| Interview Round | Select | Phone Screen, Technical, Case Study, Hiring Manager, Panel, Final |
| Interview Date | Date | Already exists. Used for the current/next round. |
| Interview Notes | Rich Text | What happened, what was discussed, Will's impressions |
| Interviewer Name | Rich Text | Who Will spoke with (name and title) |
| Next Step | Rich Text | What the company said happens next |
| Expected Response By | Date | When Will should hear back. Drives follow-up nudges. |
| NotebookLM Status | Select or Text | Tracks whether prep materials were generated. Already used by prep.py. |

- [x] Add interview properties to Notion database → Done. Properties: Interview Round, Interviewer Name, Next Step, Expected Response By.
- [ ] Build interview lifecycle into dashboard Pipeline tab
- [ ] Connect Prep button to NotebookLM notebook URL

---

## Follow-Up Tracking: New Feature (Not in Original Plan)

The original plan's "Applied" status has no post-application workflow. The dashboard shows "Applied 15 days ago, consider following up" but gives Will no tools to act on it.

**What needs to exist:**

| Feature | How it works |
|---------|-------------|
| Follow-up logging | Will taps "I followed up" and optionally logs a note. Dashboard writes the date to Notion. |
| Timer reset | After logging a follow-up, the nudge timer resets. Next nudge appears 7-10 days later. |
| Follow-up templates | Pre-written email templates Will can copy. Short, professional, customized with company name and role. |
| Auto-archive threshold | Jobs in "Applied" status with no activity for 30+ days get flagged as "No Response." Will can dismiss or keep watching. |

**New Notion properties:**

| Property | Type | Purpose |
|----------|------|---------|
| Last Follow-Up Date | Date | When Will last followed up. Drives nudge timing. |
| Follow-Up Count | Number | How many times Will has followed up on this job |
| Follow-Up Notes | Rich Text | What was said, who was contacted |

- [x] Add follow-up properties to Notion database → Done. Properties: Last Follow-Up Date, Follow-Up Count, Follow-Up Notes.
- [ ] Build follow-up actions into dashboard Applied section
- [ ] Write 2-3 follow-up email templates

---

## Recruiting Contacts: Surface Existing Data

The Notion database already has Recruiter Name, Recruiter Contact, and Internal Connection fields. The dashboard ignores all three.

These should appear in the expanded card view, especially for jobs in Applied and Interviewing status where knowing "Marcus referred me" or "recruiter is Sarah Chen, sarah@medshield.com" is directly actionable.

- [ ] Add contact fields to expanded card in dashboard

---

## Undo: Missing From All Actions

Will can dismiss a job, mark it applied, approve a resume, and bookmark/unbookmark. None of these have an undo mechanism in the dashboard. If Will taps the wrong button, he has to go into Notion and reverse it manually.

**Fix:** Add a 3-second undo window to the toast notification for destructive actions (dismiss, mark applied). The toast shows the action with an "Undo" button. If Will taps it, the state reverts. If the timer expires, the write to Notion goes through.

- [ ] Add undo to toast for dismiss and mark applied actions

---

## Notion Two-Way Sync: Rules

Will might update jobs in Notion directly (especially on desktop) or through the dashboard (especially on mobile). Both write to the same database. The sync rules:

| Scenario | Rule |
|----------|------|
| Will bookmarks in dashboard | Writes `Bookmarked = true` to Notion immediately |
| Will checks "Pursue" in Notion | Dashboard reads it on next load. Same effect as bookmarking. |
| Will dismisses in dashboard | Writes `Dismissed = true` to Notion immediately |
| Will unchecks Dismissed in Notion | Dashboard reads it on next load. Job reappears. |
| Will edits notes in dashboard | Writes to Notion on save. Overwrites whatever was in Notion. |
| Will edits notes in Notion | Dashboard reads the Notion version on next load |
| Conflict (both edited between loads) | Last write wins. Notion is the source of truth for reads. Dashboard writes go to Notion immediately. |

"Last write wins" is acceptable for a single-user system. If this becomes multi-user beyond Tanya and Will, we'd need conflict resolution.

---

## Updated Build Order

The original plan had 7 steps. Here's the revised order with the dashboard and new features included.

| Step | Task | Tool | Depends On | Status |
|------|------|------|-----------|--------|
| 1 | Delete 3 OFF Zaps in Zapier | Zapier | Nothing | Not started |
| 2 | Add new Notion properties | Notion | Nothing | Done |
| 3 | Build Monday Kickoff Email | Google Apps Script | Notion database | Not started |
| 4 | Build Claude Code job discovery pipeline | Claude Code | Notion database | Not started |
| 5 | On-site hard dealbreaker in scoring | Claude Code | Step 4 | Done |
| 6 | Interview prep materials engine + NotebookLM integration | Claude Code | Notion database | Done |
| 7 | Test pipeline end-to-end | All tools | Steps 1-6 | Not started |
| 8 | Build Vercel dashboard v1 | Vercel, Next.js | Notion database | Prototype built |
| 9 | Set up Cowork auto-trigger | Cowork | Steps 7-8 | Not started |
| 10 | Build interview lifecycle into dashboard | Vercel | Step 8 | Not started |
| 11 | Build follow-up tracking into dashboard | Vercel | Step 8 | Not started |
| 12 | Slim daily digest email | Google Apps Script | Step 8 | Not started |
| 13 | Resolve notification strategy | TBD | Steps 8-11 | Deferred |

### Where to build each step

**Step 1:** Log into Zapier dashboard. Delete: Daily Job Digest (OFF), Zap 1 New Job Alert (OFF), Weekly Digest (OFF). Keep: Zap 2 (Interview Prep Alert) and Zap 4 (Deadline Reminders).

**Step 3:** Google Apps Script project "Will's Job Digest" (same project as daily digest). Create new function `sendMondayKickoff`. Add time-based trigger for Monday mornings.

**Step 4:** Claude Code repo. Build discovery pipeline in `discovery/` directory. The scoring spec, location filter, and Notion writer already exist. The missing piece is the job board scanner.

**Step 7:** Manual testing. Run the pipeline overnight. Check: jobs appear in Notion with correct scores and properties. End-to-end takes one full week to validate all triggers.

**Step 8:** New GitHub repo or Vercel project. Initialize with `npx create-next-app@latest`.

```
app/
  layout.tsx              (root layout, global styles, Inter font)
  page.tsx                (redirect to /dashboard)
  api/
    auth/[...nextauth]/route.ts  (NextAuth config, 2 credential accounts)
    jobs/
      route.ts                   (GET: query Notion for all active jobs)
      [id]/
        bookmark/route.ts        (PATCH: toggle Bookmarked in Notion)
        dismiss/route.ts         (PATCH: set Dismissed + reason in Notion)
        apply/route.ts           (PATCH: set Applied + date in Notion)
        approve-resume/route.ts  (PATCH: set Resume Review Status = Approved)
        followup/route.ts        (PATCH: write Last Follow-Up Date + count)
        note/route.ts            (PATCH: update Notes field in Notion)
    add-job/route.ts             (POST: create new page in Notion)
  dashboard/
    page.tsx              (main dashboard, tabs, state management)
    components/
      JobCard.tsx          (Review tab card with bookmark/dismiss)
      PipelineView.tsx     (Pipeline tab with Pursuing/Applied/Interviewing)
      ResumeReview.tsx     (inline resume review component)
      MondayBanner.tsx     (Monday kickoff banner)
      AddJobOverlay.tsx    (full-screen add job form)
      Toast.tsx            (toast with undo support)
lib/
  notion.ts               (Notion API client, shared query functions)
  auth.ts                 (NextAuth config)
middleware.ts             (auth middleware, protect /dashboard routes)
```

**Step 9:** Cowork desktop automation. Trigger: watch for `Bookmarked = true AND Resume Review Status = "Not Started"` in Notion.

**Steps 10-11:** Same Vercel project, `PipelineView.tsx`.

**Step 12:** Google Apps Script project "Will's Job Digest". Modify `sendDailyDigest` function.

**Step 13:** Evaluate after Will uses dashboard for 1 week.

---

## Open Decisions

These need answers before building. Collected here for quick reference.

- [ ] Cover letters: Bundle into resume review, separate file link, or skip unless required?
- [ ] Notification strategy: Browser push, lightweight email, or keep current emails as-is?
- [ ] Monday Kickoff: Dashboard-only, email-only, or both?
- [x] ~~NotebookLM Prep button:~~ Resolved. Read NotebookLM URLs from Notion. Open notebook URL on tap, or show fallback if NotebookLM Status is still processing.
- [ ] Auto-archive threshold: 30 days in Applied with no response. Auto-dismiss, flag for review, or just show a stronger nudge?

---

## New Notion Properties Summary

All new fields needed across the system. Added to the existing database.

| Property | Type | Added For | Status |
|----------|------|----------|--------|
| Bookmarked | Checkbox | Dashboard bookmark/shortlist | Added |
| Interview Round | Select | Interview lifecycle | Added |
| Interviewer Name | Rich Text | Interview lifecycle | Added |
| Next Step | Rich Text | Interview lifecycle | Added |
| Expected Response By | Date | Interview lifecycle / follow-up nudges | Added |
| Tailored Summary | Rich Text | Inline resume review | Added |
| Skills Emphasized | Rich Text | Inline resume review | Added |
| Experience Framing | Rich Text | Inline resume review | Added |
| Last Follow-Up Date | Date | Follow-up tracking | Added |
| Follow-Up Count | Number | Follow-up tracking | Added |
| Follow-Up Notes | Rich Text | Follow-up tracking | Added |
| Recruiter Name | Rich Text | Contact tracking | Added |
| Recruiter Contact | Rich Text | Contact tracking | Added |
| Internal Connection | Rich Text | Contact tracking | Added |

**Already existed in the database (no changes needed):**

| Property | Type | Used By |
|----------|------|---------|
| Resume Review Status | Select | Dashboard resume flow |
| NotebookLM Status | Select | prep.py interview prep engine |
| NotebookLM URLs | Rich Text | Links to generated notebooks |
| Ready to Apply | Checkbox | Secondary signal alongside Bookmarked |
| Resume Version ID | Rich Text | System file tracking |
| Cover Letter | Rich Text | Cover letter content (still needs dashboard integration) |

That brings the total to 47 properties. The dashboard surfaces about 15-20 of them depending on the job's status and which tab Will is viewing. The rest stay in Notion for the pipeline, prep engine, and archival.
