import os

import requests
from mcp.server.mcpserver import MCPServer

API_BASE_URL = os.environ.get("WORKHUB_API_URL", "http://localhost:8082/api")

session = requests.Session()
session.headers["X-API-Key"] = os.environ["WORKHUB_API_KEY"]

server = MCPServer("workhub")


@server.tool()
def list_roster(requester_platform: str, requester_platform_user_id: str) -> dict:
    """List all team members with their domain skills, platform handles, and Jira account ids.
    Restricted to roster members with the "manager" role — anyone else gets an authorization error.

    requester_platform / requester_platform_user_id: identifies who is asking, so the role
    check can be enforced server-side.
    """
    response = session.get(
        f"{API_BASE_URL}/roster/",
        params={"requester_platform": requester_platform, "requester_platform_user_id": requester_platform_user_id},
        timeout=10,
    )
    if response.status_code in (403, 404):
        return {"error": response.json().get("detail", "request denied")}
    response.raise_for_status()
    return {"members": response.json()}


@server.tool()
def create_task_ticket(
    platform: str,
    channel: str,
    user: str,
    title: str,
    description: str,
    priority: str,
    domain_tags: list[str],
    complexity: str = "simple",
    scenario: str = "",
    requirements: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict:
    """Create a Jira ticket for a piece of work you've identified in a message. You do the
    classification and extraction yourself — this tool only routes (by matching domain_tags
    against the roster's skills, preferring a senior person for complex work) and creates the
    ticket, it does no reasoning of its own.

    platform: source platform, e.g. "slack" or "discord".
    channel: the channel/room the request came from.
    user: display name or handle of the person who asked for it.
    title: short imperative ticket title, e.g. "Add SSO to login page".
    description: 1-3 sentence summary of the work.
    priority: "low", "medium", or "high" — how urgent it is.
    domain_tags: 1-3 values chosen from: frontend, backend, api, database, design, devops,
        mobile, qa, docs.
    complexity: "simple" or "complex" — how involved the work itself is. Judge this independently
        of priority (an urgent task can still be simple; a complex task might not be urgent).
        "complex" routes to the most senior person among the matching skill set, when one exists.
    scenario: optional — a short narrative of the situation/context this task addresses, when
        there's enough information in the message to write one. Leave empty if not applicable.
    requirements: optional — a bullet list of what needs to be built/changed, when you can
        reasonably infer specifics from the message. Leave empty if there isn't enough to go on.
    acceptance_criteria: optional — a bullet list of concrete, checkable conditions for calling
        this done. Leave empty if there isn't enough information to write real ones — don't
        invent generic filler criteria just to fill the section.
    """
    response = session.post(
        f"{API_BASE_URL}/tasks/create/",
        json={
            "platform": platform,
            "channel": channel,
            "user": user,
            "title": title,
            "description": description,
            "priority": priority,
            "domain_tags": domain_tags,
            "complexity": complexity,
            "scenario": scenario,
            "requirements": requirements or [],
            "acceptance_criteria": acceptance_criteria or [],
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


@server.tool()
def lookup_member(platform: str, platform_user_id: str) -> dict:
    """Check whether a person is already known in the team roster, identified by their id on a
    given chat platform.

    platform: "slack", "discord", or "teams".
    platform_user_id: their user id/handle on that platform.

    Returns {"found": true, "member": {...}} or {"found": false}.
    """
    response = session.get(
        f"{API_BASE_URL}/members/lookup/",
        params={"platform": platform, "platform_user_id": platform_user_id},
        timeout=10,
    )
    if response.status_code == 404:
        return {"found": False}
    response.raise_for_status()
    return {"found": True, "member": response.json()}


@server.tool()
def onboard_member(
    platform: str,
    platform_user_id: str,
    name: str,
    github_handle: str = "",
    domain_tags: list[str] | None = None,
    preferred_platform: str | None = None,
) -> dict:
    """Register a new person in the team roster from their chat-platform identity. If they're
    already registered, returns their existing record unchanged rather than duplicating it.

    platform: the chat platform they're onboarding from ("slack", "discord", or "teams").
    platform_user_id: their user id/handle on that platform.
    name: their display name.
    github_handle: their GitHub username, if they have one.
    domain_tags: skill areas for task routing, e.g. ["frontend", "backend"].
    preferred_platform: where they'd like to be notified; defaults to `platform` if omitted.
    """
    payload = {
        "platform": platform,
        "platform_user_id": platform_user_id,
        "name": name,
        "github_handle": github_handle,
        "domain_tags": domain_tags or [],
    }
    if preferred_platform:
        payload["preferred_platform"] = preferred_platform
    response = session.post(f"{API_BASE_URL}/members/onboard/", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


@server.tool()
def get_team_status(
    requester_platform: str,
    requester_platform_user_id: str,
    target_name: str = "",
    since_hours: int = 24,
) -> dict:
    """Get recent ticket activity grouped by assignee. Restricted to roster members with the
    "manager" role — anyone else gets an authorization error back.

    requester_platform / requester_platform_user_id: identifies who is asking, so the role
    check can be enforced server-side.
    target_name: optional, filter to one person's tickets (matched loosely by name).
    since_hours: how far back to look, default 24 (roughly "yesterday").
    """
    params = {
        "requester_platform": requester_platform,
        "requester_platform_user_id": requester_platform_user_id,
        "since_hours": since_hours,
    }
    if target_name:
        params["target_name"] = target_name
    response = session.get(f"{API_BASE_URL}/status/team/", params=params, timeout=10)
    if response.status_code in (403, 404):
        return {"error": response.json().get("detail", "request denied")}
    response.raise_for_status()
    return response.json()


@server.tool()
def get_github_status(repo: str = "") -> dict:
    """Get recent pull request and issue activity for a GitHub repo (read-only, no write access).
    Flags open PRs with no activity in 48+ hours as stale, and links any PR/issue whose title or
    body mentions a Jira ticket (e.g. "SH-123") via linked_ticket.

    repo: "owner/name", e.g. "righty2004/flagionary-bot". Leave empty to use the default repo
    configured on the backend.
    """
    params = {"repo": repo} if repo else {}
    response = session.get(f"{API_BASE_URL}/github/status/", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    server.run(transport="stdio")
