from rest_framework.response import Response

from .models import PLATFORM_ID_FIELDS, RosterMember


def resolve_manager(platform: str, platform_user_id: str) -> tuple[RosterMember | None, Response | None]:
    """Resolve a requester and confirm they're a manager. Returns (member, None) on success,
    or (None, error_response) if they're unknown or not a manager."""
    field_name = PLATFORM_ID_FIELDS[platform]
    requester = RosterMember.objects.filter(**{field_name: platform_user_id}).first()
    if requester is None:
        return None, Response({"detail": "unknown requester"}, status=404)
    if requester.role != "manager":
        return None, Response({"detail": "not authorized: manager role required"}, status=403)
    return requester, None
