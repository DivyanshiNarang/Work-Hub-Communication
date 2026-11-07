from django.db import models

from roster.models import RosterMember


class IngestedEvent(models.Model):
    CATEGORY_CHOICES = [
        ("task_request", "Task request"),
        ("status_update", "Status update"),
        ("blocker", "Blocker"),
        ("noise", "Noise"),
    ]

    platform = models.CharField(max_length=20)
    channel = models.CharField(max_length=200)
    user = models.CharField(max_length=150)
    text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"[{self.category}] {self.platform}#{self.channel} {self.user}"


class TaskTicket(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    COMPLEXITY_CHOICES = [
        ("simple", "Simple"),
        ("complex", "Complex"),
    ]

    event = models.OneToOneField(IngestedEvent, on_delete=models.CASCADE, related_name="ticket")
    title = models.CharField(max_length=300)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    complexity = models.CharField(max_length=10, choices=COMPLEXITY_CHOICES, default="simple")
    domain_tags = models.JSONField(default=list)
    assignee = models.ForeignKey(RosterMember, on_delete=models.PROTECT, related_name="tickets")
    jira_key = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.jira_key}: {self.title}"
