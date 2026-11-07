from rest_framework import serializers

from roster.models import PLATFORM_ID_FIELDS
from roster.serializers import RosterMemberSerializer

from .models import TaskTicket


class TaskCreateSerializer(serializers.Serializer):
    platform = serializers.CharField(max_length=20)
    channel = serializers.CharField(max_length=200)
    user = serializers.CharField(max_length=150)
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    priority = serializers.ChoiceField(choices=TaskTicket.PRIORITY_CHOICES)
    complexity = serializers.ChoiceField(choices=TaskTicket.COMPLEXITY_CHOICES, default="simple")
    domain_tags = serializers.ListField(child=serializers.CharField())
    scenario = serializers.CharField(required=False, allow_blank=True, default="")
    requirements = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    acceptance_criteria = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class TaskTicketSerializer(serializers.ModelSerializer):
    assignee = RosterMemberSerializer(read_only=True)

    class Meta:
        model = TaskTicket
        fields = [
            "jira_key",
            "title",
            "description",
            "priority",
            "complexity",
            "domain_tags",
            "assignee",
            "created_at",
        ]


class TeamStatusQuerySerializer(serializers.Serializer):
    requester_platform = serializers.ChoiceField(choices=list(PLATFORM_ID_FIELDS))
    requester_platform_user_id = serializers.CharField()
    target_name = serializers.CharField(required=False, allow_blank=True)
    since_hours = serializers.IntegerField(required=False, default=24, min_value=1)


class GithubStatusQuerySerializer(serializers.Serializer):
    repo = serializers.CharField(required=False, allow_blank=True)
