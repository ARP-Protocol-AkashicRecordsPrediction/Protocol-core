from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgendaViewSet,
    MemoryTopicViewSet,
    PersonaInstanceViewSet,
    PopulationClusterViewSet,
    PredictionRunViewSet,
)

router = DefaultRouter()
router.register("agendas", AgendaViewSet, basename="agenda")
router.register("clusters", PopulationClusterViewSet, basename="cluster")
router.register("personas", PersonaInstanceViewSet, basename="persona")
router.register("prediction-runs", PredictionRunViewSet, basename="prediction-run")
router.register("topics", MemoryTopicViewSet, basename="topic")

urlpatterns = [
    path("", include(router.urls)),
]

