from typing import TypedDict

import requests
from django.conf import settings

from roster.models import RosterMember


class ExtractedTask(TypedDict):
    title: str
    description: str
    priority: str
    complexity: str
    domain_tags: list[str]
    scenario: str
    requirements: list[str]
    acceptance_criteria: list[str]


def _text(text: str, bold: bool = False) -> dict:
    node = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def _paragraph(text: str, bold: bool = False) -> dict:
    return {"type": "paragraph", "content": [_text(text, bold)]}


def _heading(text: str, level: int = 3) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(text)]}


def _label_bullet_list(items: list[tuple[str, str]]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [{"type": "paragraph", "content": [_text(f"{label}: ", bold=True), _text(value)]}],
            }
            for label, value in items
        ],
    }


def _plain_bullet_list(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [_paragraph(item)]} for item in items],
    }


def _build_description(task: ExtractedTask, assignee: RosterMember, source_ref: str) -> dict:
    """Jira Cloud's API v3 requires the description field as Atlassian Document Format,
    not a plain string."""
    content = [_paragraph(task["description"])]

    if task.get("scenario"):
        content += [_heading("Scenario"), _paragraph(task["scenario"])]

    if task.get("requirements"):
        content += [_heading("Requirements"), _plain_bullet_list(task["requirements"])]

    if task.get("acceptance_criteria"):
        content += [_heading("Acceptance Criteria"), _plain_bullet_list(task["acceptance_criteria"])]

    content += [
        _heading("Details"),
        _label_bullet_list(
            [
                ("Assigned to", f"{assignee.name} ({assignee.get_seniority_display()})"),
                ("Domain", ", ".join(task["domain_tags"])),
                ("Priority", task["priority"].capitalize()),
                ("Complexity", task["complexity"].capitalize()),
                ("Requested via", source_ref),
            ]
        ),
    ]

    return {"type": "doc", "version": 1, "content": content}


def create_ticket(task: ExtractedTask, assignee: RosterMember, source_ref: str) -> str:
    dry_run = not all(
        [settings.JIRA_BASE_URL, settings.JIRA_EMAIL, settings.JIRA_API_TOKEN, settings.JIRA_PROJECT_KEY]
    )
    if dry_run:
        print(
            f"[jira dry-run] would create ticket {task['title']!r} "
            f"(priority={task['priority']}) -> {assignee.name}, source: {source_ref}"
        )
        return "DRY-RUN-TICKET"

    payload = {
        "fields": {
            "project": {"key": settings.JIRA_PROJECT_KEY},
            "summary": task["title"],
            "description": _build_description(task, assignee, source_ref),
            "issuetype": {"name": "Task"},
            "assignee": {"accountId": assignee.jira_account_id},
            "priority": {"name": task["priority"].capitalize()},
        }
    }
    response = requests.post(
        f"{settings.JIRA_BASE_URL}/rest/api/3/issue",
        json=payload,
        auth=(settings.JIRA_EMAIL, settings.JIRA_API_TOKEN),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["key"]
