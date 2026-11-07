from django.urls import path

from .views import CreateTaskTicketView, GithubStatusView, TeamStatusView

urlpatterns = [
    path("tasks/create/", CreateTaskTicketView.as_view(), name="task-create"),
    path("status/team/", TeamStatusView.as_view(), name="team-status"),
    path("github/status/", GithubStatusView.as_view(), name="github-status"),
]
