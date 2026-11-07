from django.conf import settings
from rest_framework.permissions import BasePermission


class HasWorkhubAPIKey(BasePermission):
    """Requires the X-API-Key header to match WORKHUB_API_KEY. Fails closed: if the key
    isn't configured at all, nothing is allowed through — never treat "unset" as "open"."""

    def has_permission(self, request, view) -> bool:
        expected = settings.WORKHUB_API_KEY
        provided = request.headers.get("X-API-Key", "")
        return bool(expected) and provided == expected
