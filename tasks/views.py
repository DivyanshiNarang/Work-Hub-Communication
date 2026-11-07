from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from roster.models import PLATFORM_ID_FIELDS, RosterMember
from roster.routing import pick_assignee

from .models import IngestedEvent, TaskTicket
from .serializers import GithubStatusQuerySerializer, TaskCreateSerializer, TaskTicketSerializer, TeamStatusQuerySerializer
from .services.github_client import get_repo_status
from .services.jira_client import create_ticket


class CreateTaskTicketView(APIView):
    """Create a Jira ticket for a task the calling agent has already identified and extracted
    from a message — this view does no classification or extraction of its own, it only routes
    (by domain_tags, matched against the roster's skills) and creates the ticket."""

    def post(self, request):
        payload = TaskCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        event = IngestedEvent.objects.create(
            platform=data["platform"],
            channel=data["channel"],
            user=data["user"],
            text=data["description"],
            category="task_request",
            confidence=1.0,
        )
        assignee = pick_assignee(data["domain_tags"], data["complexity"])
        channel = data["channel"].lstrip("#")
        source_ref = f"{data['platform']}#{channel} by {data['user']}"
        jira_key = create_ticket(data, assignee, source_ref)
        ticket = TaskTicket.objects.create(
            event=event,
            title=data["title"],
            description=data["description"],
            priority=data["priority"],
            complexity=data["complexity"],
            domain_tags=data["domain_tags"],
            assignee=assignee,
            jira_key=jira_key,
        )
        return Response(TaskTicketSerializer(ticket).data, status=201)


class TeamStatusView(APIView):
    """Recent ticket activity, grouped by assignee. Anyone can ask about their own status;
    asking about someone else's (or the whole team's) requires role=manager."""

    def get(self, request):
        payload = TeamStatusQuerySerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        field_name = PLATFORM_ID_FIELDS[data["requester_platform"]]
        requester = RosterMember.objects.filter(**{field_name: data["requester_platform_user_id"]}).first()
        if requester is None:
            return Response({"detail": "unknown requester"}, status=404)

        target_name = data.get("target_name", "").strip()
        asking_about_self = not target_name or target_name.lower() in requester.name.lower()

        if requester.role != "manager":
            if not asking_about_self:
                return Response(
                    {"detail": "not authorized: manager role required to view someone else's status"},
                    status=403,
                )
            target_name = requester.name  # non-managers only ever see their own tickets

        cutoff = timezone.now() - timedelta(hours=data["since_hours"])
        tickets = TaskTicket.objects.select_related("assignee").filter(created_at__gte=cutoff).order_by("-created_at")
        if target_name:
            tickets = tickets.filter(assignee__name__icontains=target_name)

        by_assignee: dict[str, list[dict]] = {}
        for ticket in tickets:
            by_assignee.setdefault(ticket.assignee.name, []).append(
                {
                    "jira_key": ticket.jira_key,
                    "title": ticket.title,
                    "priority": ticket.priority,
                    "created_at": ticket.created_at.isoformat(),
                }
            )
        return Response(by_assignee)


class GithubStatusView(APIView):
    """Read-only pull request and issue status for a GitHub repo, polled on demand."""

    def get(self, request):
        payload = GithubStatusQuerySerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        repo = data.get("repo") or (settings.GITHUB_REPOS.split(",")[0].strip() if settings.GITHUB_REPOS else "")
        if not repo:
            return Response({"detail": "no repo configured or provided"}, status=400)
        if not settings.GITHUB_TOKEN:
            return Response({"detail": "GITHUB_TOKEN is not configured"}, status=503)

        return Response(get_repo_status(repo))
