from django.contrib import admin

from .models import RosterMember


@admin.register(RosterMember)
class RosterMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "domain_tags", "preferred_platform", "github_handle")
    list_filter = ("role",)
    search_fields = ("name", "github_handle")
