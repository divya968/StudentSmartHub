from django.contrib import admin
from django.urls import path, include
from dashboard.views import dashboard_view
from hub import views as hub_views
from django.shortcuts import redirect

urlpatterns = [
    path("notes/", include("study_notes.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("planner/", include("planner.urls")),
    path("pyq/", include("pyq.urls")),
    path("hub/", include("hub.urls")),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("manifest.json", hub_views.manifest, name="manifest"),
    path("sw.js", hub_views.service_worker, name="service_worker"),
    path("offline/", hub_views.offline, name="offline"),
    path("", lambda request: redirect("login")),
]


from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
