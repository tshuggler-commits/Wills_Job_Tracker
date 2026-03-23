## Branch & Commit Rules
- NEVER commit directly to `main`. Always create a feature branch first.
- Branch naming: `[type]/[short-description]` where type is one of:
  feature/, fix/, update/, beta/, prompt/, config/, docs/
- Commit message format: `type: short description` (e.g., `feat: add restaurant tracker page`)
- Keep commits under 72 characters, present tense, no period at the end
- Before starting work, always run `git checkout main && git pull origin main`
  then create a new branch with `git checkout -b type/description`
- After finishing work, push the branch with `git push origin branch-name`.
  Do NOT merge into main. Open a PR on GitHub instead.
- When working on an existing branch, always pull latest first:
  `git pull origin branch-name`

## Environment Variables
- Never hardcode Notion database IDs, API keys, or secrets in source code.
- All secrets go in environment variables. Reference them via `process.env.VARIABLE_NAME`.
- New database connections require a new env var added to both `.env.local`
  and Vercel's environment variables dashboard.

## Code Quality
- No CORS wildcard (`*`). Restrict origins to the Vercel production domain.
- Every UI element that implies an action (buttons, badges, status indicators)
  must be wired to actual functionality. No fake states or placeholder behaviors.
- API calls go in useEffect hooks or event handlers. No hardcoded seed data in production components.
- Loading states and error handling are required for every API call.
