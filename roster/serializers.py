from rest_framework import serializers

from .models import PLATFORM_ID_FIELDS, RosterMember


class RosterMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterMember
        fields = [
            "id",
            "name",
            "role",
            "seniority",
            "jira_account_id",
            "github_handle",
            "slack_id",
            "discord_id",
            "teams_id",
            "domain_tags",
            "preferred_platform",
        ]


class MemberLookupSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=list(PLATFORM_ID_FIELDS))
    platform_user_id = serializers.CharField()


class RequesterAuthSerializer(serializers.Serializer):
    requester_platform = serializers.ChoiceField(choices=list(PLATFORM_ID_FIELDS))
    requester_platform_user_id = serializers.CharField()


class MemberOnboardSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=list(PLATFORM_ID_FIELDS))
    platform_user_id = serializers.CharField()
    name = serializers.CharField(max_length=150)
    github_handle = serializers.CharField(max_length=150, required=False, allow_blank=True)
    domain_tags = serializers.ListField(child=serializers.CharField(), required=False)
    preferred_platform = serializers.ChoiceField(choices=list(PLATFORM_ID_FIELDS), required=False)
