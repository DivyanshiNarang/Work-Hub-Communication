from django.db import models

PLATFORM_ID_FIELDS = {
    "slack": "slack_id",
    "discord": "discord_id",
    "teams": "teams_id",
}


class RosterMember(models.Model):
    PLATFORM_CHOICES = [
        ("slack", "Slack"),
        ("discord", "Discord"),
        ("teams", "Microsoft Teams"),
    ]

    ROLE_CHOICES = [
        ("member", "Member"),
        ("manager", "Manager / PM"),
    ]

    SENIORITY_CHOICES = [
        ("junior", "Junior"),
        ("mid", "Mid-level"),
        ("senior", "Senior"),
    ]

    name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="member",
        help_text="Controls access to team-wide tools (e.g. viewing others' status). Set by an admin, never self-service.",
    )
    seniority = models.CharField(max_length=10, choices=SENIORITY_CHOICES, default="mid")
    jira_account_id = models.CharField(max_length=150, blank=True)
    github_handle = models.CharField(max_length=150, blank=True)
    slack_id = models.CharField(max_length=150, blank=True)
    discord_id = models.CharField(max_length=150, blank=True)
    teams_id = models.CharField(max_length=150, blank=True)
    domain_tags = models.JSONField(default=list, help_text="e.g. [\"frontend\", \"design\"]")
    preferred_platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default="slack")

    def __str__(self) -> str:
        return self.name
