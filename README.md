# Workhub — a work-hub agent for Slack, Discord, and Teams

**Built for the Flip the Switch Hackathon (WeMakeDevs × Switch AI) — Track 01: Best Business Workflow.**

Workhub turns an AI teammate sitting in your Slack, Discord, or Microsoft Teams channel into a
real coordination layer for your team: it onboards new teammates conversationally, turns a plain
message describing work into a fully-specified Jira ticket routed to the right person by skill
*and* seniority, answers "what have I been working on" without anyone opening Jira, and gives
PMs a gated view into team-wide activity and GitHub PR/issue status — all without leaving chat.

## The problem

Requirements get lost in chat threads. PMs manually re-type what someone said into a Jira ticket,
guess who should own it, and then separately ping people for status updates. None of this needs a
human in the loop — it needs a teammate who's always listening, always available, and knows the
team's skills well enough to route work correctly the first time.

## What it actually does (all of this is real and tested end-to-end, not mocked)

### 1. Conversational onboarding
The first time someone talks to the bot, it doesn't fail or ignore them — it asks for their name,
GitHub handle, what they work on, and their preferred platform, then registers them. Every
message after that, it already knows who it's talking to.

### 2. Task → Jira ticket, fully specified
Describe a piece of work in plain language in any connected channel, and the agent:
- Extracts a title, description, priority, and domain (frontend/backend/api/database/design/
  devops/mobile/qa/docs) itself — no separate classification API call, the agent *is* the LLM.
- Judges how **complex** the work is, independently of urgency, and writes a **Scenario**,
  **Requirements**, and **Acceptance Criteria** section when there's enough in the message to
  support real ones (never invented filler — a terse request gets a terse ticket).
- Routes it to the right person by skill match. For complex work, it prefers the most **senior**
  matching person; for simple work, it prefers the least senior, freeing seniors up for the work
  that actually needs them.
- Creates a real Jira ticket via the Jira Cloud REST API, formatted with real headings and bullet
  lists (Atlassian Document Format), not a plain-text dump.

### 3. Status, without manager-only being a privacy hole
Anyone can ask for their *own* recent ticket activity — no special permission needed. Asking
about *someone else's* status, or the whole team's, requires the `manager`/PM role, which is set
by an admin, never self-service (nobody can just claim to be the PM in chat).

### 4. Team roster, gated
The full directory (names, skills, platform handles, Jira account IDs) is manager-only — everyone
needs to be *in* the roster for routing to work, but not everyone should be able to list everyone
else's platform IDs on request.

### 5. GitHub status, read-only
Pull the current PR/issue state for a connected repo: what's open, what's merged, what's stale
(no activity in 48+ hours), and what's linked to a Jira ticket (parsed from `PROJ-123`-style
references in the PR/issue title or body).

## Architecture

Switch doesn't ship agents or first-party Jira/GitHub connectors — it's purely the room/transport
layer that puts an existing agent (here, Claude) into your Slack/Discord/Teams channels with
shared context and history. Everything domain-specific is ours, reached through an MCP server:

```
 Slack / Discord / Teams channel
          │  (Switch room — agent reads messages, decides what to do)
          ▼
   Switch-managed agent (Claude)
          │  calls tools over MCP
          ▼
┌─────────────────────────────────────────────────────┐
│  mcp_server/server.py  (stdio MCP server)            │
│  lookup_member · onboard_member · create_task_ticket │
│  get_team_status · list_roster · get_github_status   │
└───────────────────────┬───────────────────────────────┘
                         │  HTTP + shared-secret API key
                         ▼
┌─────────────────────────────────────────────────────┐
│  Django backend (this repo)                          │
│  roster app  — skill/seniority routing, role gating  │
│  tasks app   — ticket creation, team status, GitHub  │
│  Postgres                                            │
└───────────┬──────────────────────────┬────────────────┘
            ▼                          ▼
      Jira Cloud API            GitHub REST API
```

The agent does all the natural-language reasoning (classification, extraction, judging
complexity, writing the ticket's narrative sections). The backend does none of that — it only
routes, persists, enforces access control, and talks to Jira/GitHub. This split means there's no
separate LLM API key or billing for our backend at all; the only "AI" cost is whatever the agent
itself already uses.

## Security

- **Shared-secret API auth**: every backend endpoint requires an `X-API-Key` header matching
  `WORKHUB_API_KEY`. Fails closed — if the key isn't configured server-side, nothing gets through,
  not everything.
- **Role-based access control**: a `role` field (`member`/`manager`) on each roster member gates
  team-wide status and the full roster listing. It's never settable through the chat-facing
  onboarding flow — only an admin can promote someone, closing off self-service privilege
  escalation ("I'm the PM, trust me").
- **Self-service exception, deliberately scoped**: anyone can see their *own* status without the
  manager role; seeing anyone else's still requires it.

## Tech stack

- **Switch** (SandboxAQ) — room/transport layer across Slack, Discord, Teams, Telegram, Mattermost
- **Django 5 + Django REST Framework** — backend API
- **PostgreSQL** — persistence (Docker), SQLite for local dev
- **Model Context Protocol (Python SDK)** — the tool bridge between the agent and the backend
- **Jira Cloud REST API v3** — real ticket creation, Atlassian Document Format descriptions
- **GitHub REST API** — read-only PR/issue polling
- **Docker Compose** — one-command local deployment, live-reloading dev setup

## Project structure

```
workhub/          Django project settings, URLs, shared API-key permission class
roster/           RosterMember model, skill+seniority routing, role gating, onboarding
tasks/            Task/ticket model, Jira client, GitHub client, team status
mcp_server/       Standalone MCP server exposing the backend as agent tools
agent_instructions/  The exact instructions pasted into Switch Console for the room agent
PLAN.md           Full feature plan, architecture notes, and roadmap
```

## Getting started

```bash
cp .env.example .env
# fill in WORKHUB_API_KEY (generate: python3 -c "import secrets; print(secrets.token_hex(32))"),
# JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN / JIRA_PROJECT_KEY,
# GITHUB_TOKEN / GITHUB_REPOS

make build
make start                 # Django + Postgres on http://localhost:8082
docker compose exec web python manage.py loaddata initial_roster   # seed the demo roster
```

Jira and GitHub are both optional for local testing — ticket creation runs in a dry-run mode
(prints what it would create) if Jira credentials aren't set, and GitHub status returns a clear
error if the token isn't configured, rather than failing unpredictably.

The seeded roster's `jira_account_id` is a placeholder (`REPLACE_WITH_REAL_JIRA_ACCOUNT_ID`) —
real ticket creation needs each assignee's real Atlassian accountId (find your own via
`GET /rest/api/3/myself` on your Jira site), set through the Django admin at `/admin/`, not by
re-editing the fixture (re-running `loaddata` is meant to be safe to repeat, so it shouldn't need
real secrets baked into it).

Run the MCP server (separate process, what Switch attaches to the room's agent):

```bash
pip install -r mcp_server/requirements.txt
WORKHUB_API_URL=http://localhost:8082/api WORKHUB_API_KEY=<same key> python mcp_server/server.py
```

Then connect it to a Switch room and paste `agent_instructions/workhub-agent.md` into the
room agent's instructions in Switch Console.

## Demo script

- *"We need SSO added to the login page, it's a pretty involved change"* → complex, high-priority
  ticket with Scenario/Requirements/Acceptance Criteria, routed to the senior frontend person.
- *"Small typo fix on the docs page"* → simple ticket, routed to the least senior matching person.
- *"What have I been working on?"* (anyone) → their own recent tickets.
- *"What's Asha's status?"* as a non-manager → clean denial. Same question as the manager → her
  ticket list.
- *"What PRs are open right now?"* → live GitHub state for the connected repo.

## What's not built yet (honestly)

- **GitHub status is repo-wide, not per-person** — there's no "what has X done on GitHub"
  cross-referenced against the roster yet.
- **Blocker escalation** — the idea of detecting "I'm stuck on X" and proactively notifying a lead
  is in the plan but not implemented; a blocker message today just gets a normal reply.
- **Unified cross-platform task inbox** — aggregating one person's open items across Slack,
  Discord, and Teams into a single view is designed (see `PLAN.md`) but not built.

See `PLAN.md` for the full original plan and architecture reasoning behind these choices.
