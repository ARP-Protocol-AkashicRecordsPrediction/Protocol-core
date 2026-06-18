"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request):
    return Response(
        {
            "status": "ok",
            "service": "Social Prediction Simulator",
            "version": "0.1.0",
        }
    )


urlpatterns = [
    path("", include("simulator.ui_urls")),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/", include("simulator.urls")),
]
