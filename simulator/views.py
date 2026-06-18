from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Agenda, ClusterState, ConversationTurn, MemoryTopic, PersonaInstance, PopulationCluster, PredictionRun
from .serializers import (
    AgendaSerializer,
    ClusterStateSerializer,
    ConversationTurnSerializer,
    ExpandClustersRequestSerializer,
    MemoryTopicSerializer,
    PersonaInstanceSerializer,
    PopulationClusterSerializer,
    PredictionRunCreateSerializer,
    PredictionRunSerializer,
    StartPredictionRunSerializer,
)
from .services.errors import SimulatorError
from .services.population_service import PopulationService
from .services.prediction_service import PredictionService
from .tasks import run_prediction_task


class ServiceErrorMixin:
    def service_error_response(self, exc: Exception, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({"detail": str(exc)}, status=status_code)


class AgendaViewSet(ServiceErrorMixin, viewsets.ModelViewSet):
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer

    @action(detail=True, methods=["post"], url_path="clusters/expand")
    def expand_clusters(self, request, pk=None):
        agenda = self.get_object()
        serializer = ExpandClustersRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            clusters = PopulationService().expand_clusters_for_agenda(
                agenda=agenda,
                seed_clusters=serializer.validated_data["seed_clusters"],
                desired_count=serializer.validated_data["desired_count"],
                generation_notes=serializer.validated_data["generation_notes"],
            )
        except SimulatorError as exc:
            return self.service_error_response(exc)
        return Response({"clusters": PopulationClusterSerializer(clusters, many=True).data})


class PopulationClusterViewSet(viewsets.ModelViewSet):
    serializer_class = PopulationClusterSerializer

    def get_queryset(self):
        queryset = PopulationCluster.objects.select_related("agenda").all()
        agenda_id = self.request.query_params.get("agenda_id")
        if agenda_id:
            queryset = queryset.filter(agenda_id=agenda_id)
        return queryset


class PersonaInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = PersonaInstanceSerializer

    def get_queryset(self):
        queryset = PersonaInstance.objects.select_related("cluster", "cluster__agenda").all()
        cluster_id = self.request.query_params.get("cluster_id")
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
        return queryset


class PredictionRunViewSet(ServiceErrorMixin, viewsets.ModelViewSet):
    queryset = PredictionRun.objects.select_related("agenda").prefetch_related("shock_events")

    def get_serializer_class(self):
        if self.action == "create":
            return PredictionRunCreateSerializer
        return PredictionRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prediction_run = serializer.save()
        return Response(PredictionRunSerializer(prediction_run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        prediction_run = self.get_object()
        serializer = StartPredictionRunSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        if prediction_run.status != PredictionRun.STATUS_PENDING:
            return Response({"detail": "Only pending runs can be started."}, status=status.HTTP_400_BAD_REQUEST)
        if serializer.validated_data["run_async"]:
            run_prediction_task.delay(str(prediction_run.id))
            prediction_run.refresh_from_db()
        else:
            try:
                PredictionService().run_prediction(prediction_run.id)
            except SimulatorError as exc:
                return self.service_error_response(exc)
            prediction_run.refresh_from_db()
        return Response(PredictionRunSerializer(prediction_run).data)

    @action(detail=True, methods=["get"])
    def states(self, request, pk=None):
        prediction_run = self.get_object()
        states = (
            ClusterState.objects.select_related("cluster", "shock_event")
            .filter(prediction_run=prediction_run)
            .order_by("shock_event__order", "cluster__name")
        )
        return Response(ClusterStateSerializer(states, many=True).data)

    @action(detail=True, methods=["get"])
    def turns(self, request, pk=None):
        prediction_run = self.get_object()
        turns = (
            ConversationTurn.objects.select_related("cluster", "shock_event", "persona_instance")
            .filter(prediction_run=prediction_run)
            .order_by("created_at")
        )
        return Response(ConversationTurnSerializer(turns, many=True).data)


class MemoryTopicViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemoryTopicSerializer

    def get_queryset(self):
        queryset = MemoryTopic.objects.select_related("agenda", "cluster").prefetch_related("links", "links__turn")
        agenda_id = self.request.query_params.get("agenda_id")
        cluster_id = self.request.query_params.get("cluster_id")
        if agenda_id:
            queryset = queryset.filter(agenda_id=agenda_id)
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
        return queryset

