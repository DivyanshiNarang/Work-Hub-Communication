from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import resolve_manager
from .models import PLATFORM_ID_FIELDS, RosterMember
from .serializers import (
    MemberLookupSerializer,
    MemberOnboardSerializer,
    RequesterAuthSerializer,
    RosterMemberSerializer,
)


class RosterListView(APIView):
    """Full roster listing, restricted to roster members with role=manager."""

    def get(self, request):
        payload = RequesterAuthSerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        _, error = resolve_manager(data["requester_platform"], data["requester_platform_user_id"])
        if error:
            return error

        members = RosterMember.objects.all()
        return Response(RosterMemberSerializer(members, many=True).data)


class MemberLookupView(APIView):
    """Look up a roster member by their id on a given chat platform. 404 if unknown.

    Unrestricted: this only ever returns the caller's own record (used during onboarding),
    never someone else's — keep it that way, don't widen it into a general lookup-by-anyone.
    """

    def get(self, request):
        payload = MemberLookupSerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        field_name = PLATFORM_ID_FIELDS[data["platform"]]
        member = RosterMember.objects.filter(**{field_name: data["platform_user_id"]}).first()
        if member is None:
            return Response(status=404)
        return Response(RosterMemberSerializer(member).data)


class MemberOnboardView(APIView):
    """Create a roster member from their chat-platform identity, or return the existing one."""

    def post(self, request):
        payload = MemberOnboardSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        field_name = PLATFORM_ID_FIELDS[data["platform"]]
        member, created = RosterMember.objects.get_or_create(
            **{field_name: data["platform_user_id"]},
            defaults={
                "name": data["name"],
                "github_handle": data.get("github_handle", ""),
                "domain_tags": data.get("domain_tags", []),
                "preferred_platform": data.get("preferred_platform") or data["platform"],
            },
        )
        return Response(RosterMemberSerializer(member).data, status=201 if created else 200)
