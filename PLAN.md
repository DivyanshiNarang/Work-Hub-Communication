# Switch Hackathon Plan — Cross-Platform AI Work Hub

## 1. One-line pitch
An agent ecosystem (built on Switch) that sits across Slack, Discord, and Teams, turns messages and voice notes into routed, assigned Jira tickets, tracks real completion status via Jira + GitHub, gives everyone a unified cross-platform task inbox, auto-escalates blockers, and gives PMs/leads an accurate daily standup recap — all without anyone switching tools.

## 2. Target prizes
- **Track 01 — Best Business Workflow ($2,000)**: primary target. "Help people and AI agents get work done" matches this project directly.
- **Code with Wispr side track ($500)**: stack this by building with Wispr Flow dictation (prompts to the coding agent, room instructions, README) and submitting the Insights scorecard. This is about *how we build*, not a feature in the product — see §8.
- Track 02 (personal/creative) — not a fit, skip.

## 3. Core problem
Teams fragment work across 3+ chat platforms, a ticketing tool, and a code host. Nobody has one accurate picture of:
- what requirements have been raised and who owns them
- what's actually done vs. still pending (chat/self-reported status is unreliable)
- what's blocked and needs escalation
- what's on their plate across platforms

## 4. Feature set

### 4.1 Task extraction → routing → Jira ticket (hero flow)
A requirement typed or spoken in any platform is classified, parsed into a structured task, matched to the right team member by skill/domain, and turned into an assigned Jira ticket — with a link posted back to the source channel.

### 4.2 Voice input (Whisper)
Voice notes/messages dropped in Slack/Discord/Teams are transcribed (OpenAI Whisper) and fed into the same pipeline as text — a spoken requirement produces a ticket exactly like a typed one.

### 4.3 GitHub as ground truth
Read-only polling of PRs/issues for each team member. PR state (open/in review/approved/merged) and stale-PR detection (no activity > N days) feed both the standup recap and blocker escalation. PR descriptions are parsed for ticket references (`Fixes PROJ-123`) to auto-link PR ↔ Jira ticket.

### 4.4 Unified task inbox
On-demand ("@bot my tasks") or pushed view, per person, aggregating everything relevant to them regardless of platform: Jira tickets assigned to them (not Done), GitHub PRs awaiting their review, open task requests addressed to them in any chat platform, active blockers flagged to them. Deduplicated by ticket/PR number as the join key, so the same item isn't shown twice because it was mentioned on two platforms.

### 4.5 Cross-platform standup recap
Scheduled digest, two outputs:
- **Personal**: "Yesterday you completed X (PR #39 merged), Y is pending (PR #42 awaiting review), Z (Issue #101) has had no activity in 2 days" — built from Jira status transitions + GitHub PR/issue state, not from re-reading chat.
- **Team rollup for PM/lead**: one line per person, same underlying data, delivered wherever the lead lives.

### 4.6 Blocker escalation
Triggered by: (a) a classifier tagging a chat message as a blocker ("stuck on X"), or (b) a stale PR with no review activity, or (c) a Jira ticket sitting in the same status too long. Escalates to the right lead/reviewer, delivered on *their* preferred platform — not necessarily the platform the blocker was raised on.

## 5. Architecture

### 5.1 What Switch actually provides (confirmed from docs.switchagents.ai)
Switch is the room/transport layer, nothing more:
- **Rooms** live inside Slack / Teams / Mattermost / Discord / Telegram channels. A room holds shared context, message history, and resource scoping for whoever (human or agent) is in it.
- **Switch ships no agents and no first-party Jira/GitHub connectors.** You bring your own agent (Claude Code, Codex, LangChain, etc. — anything that speaks "the agent protocol") and invite it into a room with a role.
- **Tools reach the agent via MCP servers** (or custom tool definitions) — GitHub/Jira/Google Workspace access is explicitly done "via tools/MCP servers," not built-in.
- Switch Trust (a separate product) handles cost/safety guardrails — not needed for this hackathon.

This means: **Switch replaces our planned Slack/Discord/Teams platform adapters entirely.** We don't write bot code per platform — Switch already puts an agent in the room across all of them. What we still need to build is everything Switch explicitly says it doesn't provide: the classification/extraction/routing/ticketing/standup/inbox/escalation logic. We expose that as **tools the in-room agent calls**, via an MCP server wrapping our backend.

### 5.2 Revised pipeline

```
Switch Room (Slack/Discord/Teams channel, agent already invited)
        │  agent reads messages/voice notes in-room, decides when to act
        ▼
   MCP Server (ours) — the tool surface the in-room agent calls:
        ├─ classify_message(text)            → task_request | status_update | blocker | noise
        ├─ create_task_ticket(text, source)  → extract → route (roster skill match) → Jira ticket
        ├─ get_my_inbox(person)              → unified cross-platform task view
        ├─ get_standup_digest(person|team)   → Jira + GitHub ground-truth recap
        └─ escalate_blocker(text, source)    → find the right lead, notify on their preferred platform
        ▼
   Django backend (this repo) — owns the actual state & external calls:
        roster/routing · tasks (classify/extract) · Jira client · GitHub client (read-only poll)
```

The Django REST API we built (`/api/roster/`, `/api/events/ingest/`) is the backend; the MCP server is a thin wrapper exposing the same operations as callable tools for whichever agent Switch puts in the room. **Open item**: confirm whether a Switch room's agent sees every message passively (so it can silently act on task requests) or only responds when addressed — this determines how much of the classify step must happen agent-side (via room instructions) vs. tool-side (via our `classify_message` tool). Need Switch Console/room access to verify.

## 6. Data model

**Roster** (static config or small table) — one row per team member:
`{ name, slack_id?, discord_id?, teams_id?, github_handle, jira_account_id, domain_tags[] (frontend/backend/design/...), preferred_platform }`

**Completion-state store** — minimal, mostly a cache over Jira/GitHub (treat Jira + GitHub as source of truth, don't duplicate state we don't have to):
`{ ticket_id, pr_number?, status, last_transition_ts, linked_platform_message_ref }`

## 7. Tech stack (suggested)
- Slack: Bolt SDK (bot token + Events API) — fastest to stand up
- Discord: discord.js bot — fastest to stand up
- Teams: Bot Framework + Graph API — **heaviest setup (Azure AD app, admin consent)**, treat as stretch
- Voice: OpenAI Whisper API
- Reasoning (classify/extract/route): Claude, called from within Switch's agent runtime
- Jira: REST API v3 (API token auth)
- GitHub: REST API via octokit/PyGithub, polling (not webhooks — avoids needing a public endpoint for the demo)
- State: SQLite (roster + lightweight cache) — don't over-build a database for a hackathon

## 8. Wispr Flow side track — separate from the product
Use Wispr Flow (Mac/Windows only — **not available on Linux**, flagged for Ritesh specifically) to dictate prompts to the coding agent, Switch room instructions, and the README while building. Capture the Insights scorecard screenshot from the Wispr Flow desktop app at submission time. This is a build-process requirement, not something embedded in the shipped product — the product's own voice feature uses Whisper (see §4.2), not Wispr Flow.

## 9. Open dependencies / questions
- ~~Switch's actual room/agent API~~ — resolved: Switch = room/transport layer only (Slack/Teams/Discord/Telegram/Mattermost), no first-party agents or Jira/GitHub connectors; tools reach the in-room agent via an MCP server. See §5.1.
- Whether a Switch room's agent passively observes every message (can act silently) or only responds when addressed — needs Switch Console/room access to verify; affects how much classification logic lives in room instructions vs. our MCP tool.
- Final roster for the demo (how many people, real or seeded test identities).
- Jira project to target (existing project or a fresh demo project).
- GitHub repo(s) in scope for the GitHub agent.
- Confirm Mac/Windows access for the Wispr Flow side-track requirement.

## 10. Build milestones (map to your actual hackathon hours)
- **M0 — Setup**: ✅ Django backend scaffolded and dockerized (`roster`, `tasks` apps, Postgres, whitenoise, `Makefile`). ✅ MCP server (`mcp_server/server.py`) wrapping the API as tools (`list_roster`, `ingest_message`), verified end-to-end against the live backend. ⬜ Switch Console install + first real Slack/Discord room (external/manual, in progress).
- **M1 — Hero flow**: ✅ classify → extract → route → Jira ticket creation implemented and tested (dry-run without Jira creds). ⬜ Needs `ANTHROPIC_API_KEY` set to actually exercise classify/extract live, and a real Switch room calling `ingest_message` in place of the current direct-curl testing.
- **M2 — GitHub agent**: read-only PR/issue polling, ticket-reference linking, stale-PR detection.
- **M3 — Inbox + Standup**: unified task inbox command, scheduled personal + team-rollup digest, Notifier dispatch to preferred platform.
- **M4 — Blocker escalation**: chat-based blocker detection + stale-PR/stuck-ticket triggers routed to the right person.
- **M5 — Voice**: Whisper transcription wired into Slack/Discord voice attachments, feeding the same pipeline.
- **M6 — Polish & submit**: demo script rehearsal, README, Wispr Flow scorecard, Teams adapter only if time allows.

## 11. Demo script (judging run-through)
1. Post a requirement in Slack → ticket created, assignee pinged on Slack; same from Discord → ticket created, assignee pinged on Discord. Shows cross-platform parity.
2. Run "my tasks" → unified inbox pulling Jira + GitHub + chat-origin items across platforms in one view.
3. Post a blocker message → escalation ping lands on the lead's preferred platform (different from where it was raised).
4. Trigger the standup digest → accurate completed/pending breakdown backed by real Jira/GitHub state, not guesses.
5. Drop a voice note → transcribed by Whisper → same pipeline creates a ticket, closing the voice story.
6. Mention the Wispr Flow scorecard for the build-process side track.

## 12. Risks to manage
- **Scope**: six features is a lot — if time runs short, cut Teams first, then blocker escalation, keeping hero flow + inbox + standup + GitHub as the core demo.
- **Teams Graph API setup overhead** — don't let this eat build time; it's the most expendable adapter.
- **GitHub webhooks vs polling** — polling avoids needing a public endpoint; keep it that way unless there's time to spare for real-time webhook automation.
- **"Done vs pending" accuracy** — always prefer Jira/GitHub state over LLM inference from chat; only fall back to chat-inference for tasks that never got ticketed.
