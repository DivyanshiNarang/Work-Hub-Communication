from django.contrib import admin
from django.urls import include, path

from roster.views import MemberLookupView, MemberOnboardView, RosterListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tasks.urls')),
    path('api/roster/', RosterListView.as_view(), name='roster-list'),
    path('api/members/lookup/', MemberLookupView.as_view(), name='member-lookup'),
    path('api/members/onboard/', MemberOnboardView.as_view(), name='member-onboard'),
]
