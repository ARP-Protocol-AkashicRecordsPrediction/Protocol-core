import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Agenda(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=240)
    description = models.TextField()
    target_region = models.CharField(max_length=120, blank=True)
    target_population = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["title"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class PopulationCluster(TimestampedModel):
    WEIGHT_EXPLICIT = "explicit"
    WEIGHT_LLM_ESTIMATED = "llm_estimated"
    WEIGHT_EQUAL_DEFAULT = "equal_default"
    WEIGHT_SOURCE_CHOICES = [
        (WEIGHT_EXPLICIT, "Explicit"),
        (WEIGHT_LLM_ESTIMATED, "LLM estimated"),
        (WEIGHT_EQUAL_DEFAULT, "Equal default"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name="clusters")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    demographics = models.JSONField(default=dict, blank=True)
    values = models.JSONField(default=dict, blank=True)
    traits = models.JSONField(default=dict, blank=True)
    media_diet = models.JSONField(default=list, blank=True)
    pain_points = models.JSONField(default=list, blank=True)
    weight = models.FloatField(default=1.0, validators=[MinValueValidator(0.0)])
    weight_source = models.CharField(
        max_length=24,
        choices=WEIGHT_SOURCE_CHOICES,
        default=WEIGHT_EQUAL_DEFAULT,
    )
    confidence = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agenda", "name"], name="unique_cluster_name_per_agenda"),
        ]
        indexes = [
            models.Index(fields=["agenda", "name"]),
            models.Index(fields=["agenda", "weight"]),
        ]
        ordering = ["agenda", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.agenda.title})"


class PersonaInstance(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster = models.ForeignKey(PopulationCluster, on_delete=models.CASCADE, related_name="personas")
    name = models.CharField(max_length=160)
    profile = models.JSONField(default=dict, blank=True)
    current_memory_summary = models.TextField(blank=True)
    recent_memory_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["cluster", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.cluster.name})"


class PredictionRun(TimestampedModel):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name="prediction_runs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    config = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True)
    opinion_distribution = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["agenda", "status"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.agenda.title} [{self.status}]"


class ShockEvent(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prediction_run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name="shock_events")
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    description = models.TextField()
    event_type = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["prediction_run", "order"], name="unique_shock_order_per_run"),
        ]
        ordering = ["prediction_run", "order"]

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"


class ClusterState(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prediction_run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name="cluster_states")
    shock_event = models.ForeignKey(ShockEvent, on_delete=models.CASCADE, related_name="cluster_states")
    cluster = models.ForeignKey(PopulationCluster, on_delete=models.CASCADE, related_name="states")
    stance = models.CharField(max_length=120)
    sentiment = models.CharField(max_length=120, blank=True)
    acceptance_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    behavior_intent = models.JSONField(default=dict, blank=True)
    risk_factors = models.JSONField(default=list, blank=True)
    reasoning = models.TextField(blank=True)
    confidence = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["prediction_run", "shock_event", "cluster"],
                name="unique_cluster_state_per_shock",
            ),
        ]
        indexes = [
            models.Index(fields=["prediction_run", "shock_event"]),
            models.Index(fields=["cluster", "created_at"]),
        ]
        ordering = ["shock_event__order", "cluster__name"]

    def __str__(self) -> str:
        return f"{self.cluster.name}: {self.stance}"


class ConversationTurn(TimestampedModel):
    SPEAKER_CLUSTER = "cluster"
    SPEAKER_PERSONA = "persona"
    SPEAKER_SYSTEM = "system"
    SPEAKER_AGGREGATOR = "aggregator"
    SPEAKER_TYPE_CHOICES = [
        (SPEAKER_CLUSTER, "Cluster"),
        (SPEAKER_PERSONA, "Persona"),
        (SPEAKER_SYSTEM, "System"),
        (SPEAKER_AGGREGATOR, "Aggregator"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prediction_run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name="turns")
    shock_event = models.ForeignKey(
        ShockEvent,
        on_delete=models.CASCADE,
        related_name="turns",
        null=True,
        blank=True,
    )
    cluster = models.ForeignKey(
        PopulationCluster,
        on_delete=models.CASCADE,
        related_name="turns",
        null=True,
        blank=True,
    )
    persona_instance = models.ForeignKey(
        PersonaInstance,
        on_delete=models.SET_NULL,
        related_name="turns",
        null=True,
        blank=True,
    )
    speaker_type = models.CharField(max_length=24, choices=SPEAKER_TYPE_CHOICES)
    text = models.TextField()
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["prediction_run", "created_at"]),
            models.Index(fields=["shock_event", "created_at"]),
            models.Index(fields=["cluster", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.speaker_type}: {self.text[:80]}"


class MemoryTopic(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name="memory_topics")
    cluster = models.ForeignKey(
        PopulationCluster,
        on_delete=models.CASCADE,
        related_name="memory_topics",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=240)
    summary = models.TextField(blank=True)
    freshness_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    importance_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agenda", "cluster", "title"], name="unique_topic_per_cluster"),
        ]
        indexes = [
            models.Index(fields=["agenda", "cluster"]),
            models.Index(fields=["importance_score", "freshness_score"]),
        ]
        ordering = ["-importance_score", "-freshness_score", "title"]

    def __str__(self) -> str:
        return self.title


class MemoryTopicLink(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(MemoryTopic, on_delete=models.CASCADE, related_name="links")
    turn = models.ForeignKey(ConversationTurn, on_delete=models.CASCADE, related_name="topic_links")
    link_reason = models.TextField(blank=True)
    confidence = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["topic", "turn"], name="unique_topic_turn_link"),
        ]
        indexes = [
            models.Index(fields=["topic", "confidence"]),
            models.Index(fields=["turn"]),
        ]

    def __str__(self) -> str:
        return f"{self.topic.title} -> {self.turn_id}"


class LLMCallLog(TimestampedModel):
    PROVIDER_GEMINI = "gemini"
    PROVIDER_OPENAI = "openai"
    PROVIDER_CHOICES = [
        (PROVIDER_GEMINI, "Gemini"),
        (PROVIDER_OPENAI, "OpenAI"),
    ]
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=24, choices=PROVIDER_CHOICES)
    model = models.CharField(max_length=120)
    purpose = models.CharField(max_length=120)
    prompt_hash = models.CharField(max_length=64)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["provider", "purpose", "status"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.purpose}:{self.status}"

