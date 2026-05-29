"""
URL configuration for carsharing_project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from carsharing.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("carsharing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
