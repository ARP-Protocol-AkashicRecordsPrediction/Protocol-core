from rest_framework import serializers

from .models import (
    Agenda,
    ClusterState,
    ConversationTurn,
    MemoryTopic,
    MemoryTopicLink,
    PersonaInstance,
    PopulationCluster,
    PredictionRun,
    ShockEvent,
)


class AgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agenda
        fields = [
            "id",
            "title",
            "description",
            "target_region",
            "target_population",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PopulationClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopulationCluster
        fields = [
            "id",
            "agenda",
            "name",
            "description",
            "demographics",
            "values",
            "traits",
            "media_diet",
            "pain_points",
            "weight",
            "weight_source",
            "confidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PersonaInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaInstance
        fields = [
            "id",
            "cluster",
            "name",
            "profile",
            "current_memory_summary",
            "recent_memory_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ShockEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShockEvent
        fields = [
            "id",
            "prediction_run",
            "order",
            "title",
            "description",
            "event_type",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "prediction_run", "created_at", "updated_at"]


class ShockEventInputSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=240)
    description = serializers.CharField()
    event_type = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    metadata = serializers.DictField(required=False, default=dict)


class PredictionRunSerializer(serializers.ModelSerializer):
    shock_events = ShockEventSerializer(many=True, read_only=True)
    state_count = serializers.SerializerMethodField()
    turn_count = serializers.SerializerMethodField()

    class Meta:
        model = PredictionRun
        fields = [
            "id",
            "agenda",
            "status",
            "config",
            "result_summary",
            "opinion_distribution",
            "started_at",
            "completed_at",
            "error_message",
            "shock_events",
            "state_count",
            "turn_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "result_summary",
            "opinion_distribution",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_state_count(self, obj):
        return obj.cluster_states.count()

    def get_turn_count(self, obj):
        return obj.turns.count()


class PredictionRunCreateSerializer(serializers.Serializer):
    agenda_id = serializers.UUIDField()
    config = serializers.DictField(required=False, default=dict)
    shock_events = ShockEventInputSerializer(many=True)

    def validate_agenda_id(self, value):
        if not Agenda.objects.filter(id=value).exists():
            raise serializers.ValidationError("Agenda does not exist.")
        return value

    def validate_shock_events(self, value):
        orders = [item["order"] for item in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError("Shock event order values must be unique.")
        return value

    def create(self, validated_data):
        agenda = Agenda.objects.get(id=validated_data["agenda_id"])
        prediction_run = PredictionRun.objects.create(
            agenda=agenda,
            config=validated_data.get("config", {}),
        )
        for item in sorted(validated_data["shock_events"], key=lambda event: event["order"]):
            ShockEvent.objects.create(prediction_run=prediction_run, **item)
        return prediction_run


class ClusterStateSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source="cluster.name", read_only=True)
    shock_order = serializers.IntegerField(source="shock_event.order", read_only=True)
    shock_title = serializers.CharField(source="shock_event.title", read_only=True)

    class Meta:
        model = ClusterState
        fields = [
            "id",
            "prediction_run",
            "shock_event",
            "shock_order",
            "shock_title",
            "cluster",
            "cluster_name",
            "stance",
            "sentiment",
            "acceptance_score",
            "behavior_intent",
            "risk_factors",
            "reasoning",
            "confidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ConversationTurnSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source="cluster.name", read_only=True)
    shock_order = serializers.IntegerField(source="shock_event.order", read_only=True)

    class Meta:
        model = ConversationTurn
        fields = [
            "id",
            "prediction_run",
            "shock_event",
            "shock_order",
            "cluster",
            "cluster_name",
            "persona_instance",
            "speaker_type",
            "text",
            "raw_payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MemoryTopicLinkSerializer(serializers.ModelSerializer):
    turn_text = serializers.CharField(source="turn.text", read_only=True)

    class Meta:
        model = MemoryTopicLink
        fields = [
            "id",
            "topic",
            "turn",
            "turn_text",
            "link_reason",
            "confidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MemoryTopicSerializer(serializers.ModelSerializer):
    links = MemoryTopicLinkSerializer(many=True, read_only=True)

    class Meta:
        model = MemoryTopic
        fields = [
            "id",
            "agenda",
            "cluster",
            "title",
            "summary",
            "freshness_score",
            "importance_score",
            "links",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExpandClustersRequestSerializer(serializers.Serializer):
    desired_count = serializers.IntegerField(min_value=1, max_value=30, default=8)
    generation_notes = serializers.CharField(required=False, allow_blank=True, default="")
    seed_clusters = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class StartPredictionRunSerializer(serializers.Serializer):
    run_async = serializers.BooleanField(default=True)

