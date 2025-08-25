"""
Root URL configuration for the project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin – Jazzmin will skin this automatically
    path("admin/", admin.site.urls),

    # Student panel app (handles register, login, dashboard, etc.)
      path("", include(("studentpanel.urls", "studentpanel"), namespace="studentpanel")),
]

# Serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
