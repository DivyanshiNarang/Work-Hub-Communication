import re
from datetime import datetime, timezone

import requests
from django.conf import settings

_TICKET_REF_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
_STALE_AFTER_HOURS = 48


def _extract_ticket_ref(text: str) -> str | None:
    match = _TICKET_REF_RE.search(text or "")
    return match.group(1) if match else None


def _is_stale(updated_at: str) -> bool:
    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
    return age_hours > _STALE_AFTER_HOURS


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def get_repo_status(repo: str) -> dict:
    pr_response = requests.get(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=_headers(),
        params={"state": "all", "per_page": 20, "sort": "updated", "direction": "desc"},
        timeout=10,
    )
    pr_response.raise_for_status()

    pull_requests = []
    for pr in pr_response.json():
        pull_requests.append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"],
                "state": "merged" if pr.get("merged_at") else pr["state"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "url": pr["html_url"],
                "linked_ticket": _extract_ticket_ref(f"{pr['title']} {pr.get('body') or ''}"),
                "stale": pr["state"] == "open" and _is_stale(pr["updated_at"]),
            }
        )

    issue_response = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        headers=_headers(),
        params={"state": "all", "per_page": 20, "sort": "updated", "direction": "desc"},
        timeout=10,
    )
    issue_response.raise_for_status()

    issues = []
    for issue in issue_response.json():
        if "pull_request" in issue:
            continue  # GitHub's issues endpoint also returns PRs; those are covered above
        issues.append(
            {
                "number": issue["number"],
                "title": issue["title"],
                "author": issue["user"]["login"],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "url": issue["html_url"],
                "linked_ticket": _extract_ticket_ref(f"{issue['title']} {issue.get('body') or ''}"),
            }
        )

    return {"repo": repo, "pull_requests": pull_requests, "issues": issues}
