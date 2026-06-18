from django.contrib import admin

from .models import (
    Agenda,
    ClusterState,
    ConversationTurn,
    LLMCallLog,
    MemoryTopic,
    MemoryTopicLink,
    PersonaInstance,
    PopulationCluster,
    PredictionRun,
    ShockEvent,
)


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ("title", "target_region", "created_at")
    search_fields = ("title", "description", "target_population")


@admin.register(PopulationCluster)
class PopulationClusterAdmin(admin.ModelAdmin):
    list_display = ("agenda", "name", "weight", "weight_source", "confidence")
    list_filter = ("weight_source", "agenda")
    search_fields = ("name", "description")


@admin.register(PersonaInstance)
class PersonaInstanceAdmin(admin.ModelAdmin):
    list_display = ("name", "cluster", "created_at")
    list_filter = ("cluster__agenda",)
    search_fields = ("name",)


@admin.register(PredictionRun)
class PredictionRunAdmin(admin.ModelAdmin):
    list_display = ("agenda", "status", "started_at", "completed_at", "created_at")
    list_filter = ("status", "agenda")


@admin.register(ShockEvent)
class ShockEventAdmin(admin.ModelAdmin):
    list_display = ("prediction_run", "order", "title", "event_type")
    list_filter = ("event_type",)
    ordering = ("prediction_run", "order")


@admin.register(ClusterState)
class ClusterStateAdmin(admin.ModelAdmin):
    list_display = ("prediction_run", "shock_event", "cluster", "stance", "acceptance_score", "confidence")
    list_filter = ("stance", "sentiment")


@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    list_display = ("prediction_run", "shock_event", "cluster", "speaker_type", "created_at")
    list_filter = ("speaker_type",)
    search_fields = ("text",)


@admin.register(MemoryTopic)
class MemoryTopicAdmin(admin.ModelAdmin):
    list_display = ("agenda", "cluster", "title", "freshness_score", "importance_score")
    search_fields = ("title", "summary")


@admin.register(MemoryTopicLink)
class MemoryTopicLinkAdmin(admin.ModelAdmin):
    list_display = ("topic", "turn", "confidence")


@admin.register(LLMCallLog)
class LLMCallLogAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "purpose", "status", "created_at")
    list_filter = ("provider", "purpose", "status")
    search_fields = ("purpose", "error_message")

