# AI Daily Digest — Scheduler

Runs every day at **10:00 AM CET** via GitHub Actions, calls the Claude API to generate
the AI briefing, and posts it to a Slack channel.

---

## Setup (one-time, ~10 minutes)

### 1. Create a GitHub repository

Push this folder's contents to a new private GitHub repo.

```bash
git init
git add .
git commit -m "Initial digest scheduler"
gh repo create ai-digest-scheduler --private --push --source=.
```

### 2. Get an Anthropic API key

Go to https://console.anthropic.com → API Keys → Create key.
The digest uses `claude-sonnet-4-6` with web search, which costs roughly **$0.05–0.15 per run**.

### 3. Set up a Slack bot

1. Go to https://api.slack.com/apps → Create New App → From scratch
2. Name it `AI Digest Bot`, pick your workspace
3. Under **OAuth & Permissions**, add these Bot Token Scopes:
   - `chat:write`
   - `chat:write.public` (if posting to public channels)
4. Click **Install to Workspace** → copy the `xoxb-...` Bot Token
5. Invite the bot to your target channel: `/invite @AI Digest Bot`

### 4. Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name        | Value                          |
|--------------------|--------------------------------|
| `ANTHROPIC_API_KEY`| Your Anthropic API key         |
| `SLACK_BOT_TOKEN`  | `xoxb-...` bot token           |
| `SLACK_CHANNEL`    | `#ai-briefing` (or the channel ID `C0XXXXXX`) |

### 5. Enable the workflow

The workflow file is at `.github/workflows/daily_digest.yml`.
Once pushed, it will appear under **Actions** in your repo and run automatically.

To test immediately: Actions → Daily AI Digest → Run workflow.

---

## Timing note

The cron is set to `0 8 * * *` (08:00 UTC), which equals:
- **10:00 AM CEST** (Belgium, Apr–Oct)
- **09:00 AM CET** (Belgium, Oct–Apr)

Adjust the cron if you want strict 10:00 AM year-round:
- Summer (CEST, UTC+2): `0 8 * * *`
- Winter (CET, UTC+1): `0 9 * * *`

Or use a tool like https://crontab.guru to set your preferred time.

---

## Files

```
.
├── digest_runner.py                    # Main script
├── .github/
│   └── workflows/
│       └── daily_digest.yml           # GitHub Actions schedule
└── README.md
```
