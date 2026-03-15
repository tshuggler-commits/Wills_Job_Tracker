# Job Tracker Notifications — Setup Guide

This replaces all Zapier email notifications with GitHub Actions + Python.
Zero manual configuration. Zero Zapier costs.

---

## What You're Deploying

| Workflow | Schedule | What It Does |
|----------|----------|-------------|
| `daily-digest.yml` | 8 AM ET daily | Emails all jobs found today, grouped by priority |
| `weekly-summary.yml` | 7 AM ET Mondays | Emails weekly match count + application count |
| `deadline-reminder.yml` | 9 AM ET daily | Emails jobs with Apply By dates 3 days out |

All three skip sending if there's nothing to report.

---

## Step 1: Add Files to Your Repo

Copy these into your existing GitHub repo (the one with the job search pipeline):

```
your-repo/
├── .github/
│   └── workflows/
│       ├── daily-digest.yml      ← from github-workflows/
│       ├── weekly-summary.yml    ← from github-workflows/
│       └── deadline-reminder.yml ← from github-workflows/
└── notifications/
    ├── notify.py                 ← from notifications/
    └── requirements.txt          ← from notifications/
```

## Step 2: Create a Gmail App Password

Gmail blocks regular passwords for SMTP. You need an app password:

1. Go to https://myaccount.google.com/apppasswords
2. Sign in with wilsharp20@gmail.com
3. You need 2-Step Verification enabled first (Security → 2-Step Verification)
4. Under "App passwords", select "Mail" and "Other (Custom name)"
5. Name it "Job Tracker Notifications"
6. Click Generate — copy the 16-character password
7. Save it somewhere safe (you'll paste it into GitHub next)

## Step 3: Add GitHub Secrets

In your GitHub repo:

1. Go to Settings → Secrets and variables → Actions
2. Add these 4 repository secrets:

| Secret Name | Value |
|-------------|-------|
| `NOTION_TOKEN` | Your Notion integration token (starts with `ntn_` or `secret_`) |
| `NOTION_DATABASE_ID` | `ac20106e-1c1c-4000-8065-f57850f48d10` |
| `GMAIL_ADDRESS` | `wilsharp20@gmail.com` |
| `GMAIL_APP_PASSWORD` | The 16-character app password from Step 2 |

If you don't have a Notion integration token yet:
1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it "Job Tracker Notifications"
4. Select your workspace
5. Copy the "Internal Integration Secret"
6. Go to your Job Tracker database in Notion
7. Click ••• (three dots) → Connections → Connect → find your integration

## Step 4: Test

You don't need to wait for the schedule. Run each workflow manually:

1. Go to your repo → Actions tab
2. Click "Daily Job Digest" in the left sidebar
3. Click "Run workflow" → "Run workflow"
4. Watch the run log for success/failure
5. Check your email

Repeat for "Weekly Job Summary" and "Deadline Reminder".

## Step 5: Turn Off Zapier

Once all three workflows are sending emails correctly:

1. Go to your Zapier dashboard
2. Turn OFF Zap 1 (Real-Time Alert) — already should be off
3. Turn OFF Zap 2 (Daily Digest)
4. Turn OFF Zap 3 (Weekly Summary)
5. Turn OFF Zap 4 (Deadline Reminder)

You can delete them later once you've confirmed GitHub Actions is working reliably
for a week or two.

---

## Timing Reference

| Time (ET) | What Happens |
|-----------|-------------|
| 7:00 AM | Job search pipeline runs → writes new jobs to Notion |
| 8:00 AM | Daily digest workflow → emails today's matches |
| 9:00 AM | Deadline reminder workflow → emails 3-day-out deadlines |
| 7:00 AM Mon | Weekly summary workflow → emails weekly rollup |

Note: GitHub Actions cron uses UTC. During EDT (March–November), emails
arrive 1 hour later than listed above. The pipeline buffer still holds.

---

## Troubleshooting

**"Error: Missing environment variables"**
→ Check that all 4 secrets are set in GitHub repo settings. Secret names are case-sensitive.

**"401 Unauthorized" from Notion**
→ Your NOTION_TOKEN is wrong or the integration isn't connected to the database.
→ Go to your Job Tracker in Notion → ••• → Connections → verify the integration is listed.

**"Authentication error" from Gmail**
→ Your GMAIL_APP_PASSWORD is wrong or expired. Generate a new one.
→ Make sure 2-Step Verification is still enabled on the Google account.

**"No new jobs found today. No email sent."**
→ This is normal when the pipeline didn't find matches. Check Notion to confirm.

**Emails arrive at wrong time**
→ GitHub cron is UTC. During EDT, subtract 4 hours. During EST, subtract 5 hours.
→ Adjust the cron expressions in the workflow files if needed.

**Want to test with a specific date?**
→ Temporarily edit notify.py to hardcode a date instead of using today's date.
→ Or add test entries to Notion with today's Date Found value.
