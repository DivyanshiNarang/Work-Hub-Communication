from django.contrib import admin

from .models import IngestedEvent, TaskTicket


@admin.register(IngestedEvent)
class IngestedEventAdmin(admin.ModelAdmin):
    list_display = ("platform", "channel", "user", "category", "created_at")
    list_filter = ("platform", "category")


@admin.register(TaskTicket)
class TaskTicketAdmin(admin.ModelAdmin):
    list_display = ("jira_key", "title", "assignee", "priority", "created_at")
    list_filter = ("priority",)
