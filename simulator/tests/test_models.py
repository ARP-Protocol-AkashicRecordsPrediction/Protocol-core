from django.db import IntegrityError, transaction
from django.test import TestCase

from simulator.models import (
    Agenda,
    ClusterState,
    ConversationTurn,
    MemoryTopic,
    MemoryTopicLink,
    PopulationCluster,
    PredictionRun,
    ShockEvent,
)


class ModelConstraintTests(TestCase):
    def setUp(self):
        self.agenda = Agenda.objects.create(
            title="AI policy",
            description="Predict reaction to a new AI disclosure policy.",
        )
        self.cluster = PopulationCluster.objects.create(
            agenda=self.agenda,
            name="Privacy skeptics",
            weight=0.4,
            confidence=0.8,
        )
        self.run = PredictionRun.objects.create(agenda=self.agenda)
        self.shock = ShockEvent.objects.create(
            prediction_run=self.run,
            order=1,
            title="Policy announcement",
            description="A new disclosure rule is announced.",
        )

    def test_cluster_name_unique_per_agenda(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PopulationCluster.objects.create(
                    agenda=self.agenda,
                    name="Privacy skeptics",
                    weight=0.2,
                )

    def test_shock_order_unique_per_run(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ShockEvent.objects.create(
                    prediction_run=self.run,
                    order=1,
                    title="Duplicate",
                    description="Duplicate order.",
                )

    def test_cluster_state_unique_per_shock(self):
        ClusterState.objects.create(
            prediction_run=self.run,
            shock_event=self.shock,
            cluster=self.cluster,
            stance="skeptical",
            acceptance_score=0.2,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClusterState.objects.create(
                    prediction_run=self.run,
                    shock_event=self.shock,
                    cluster=self.cluster,
                    stance="supportive",
                    acceptance_score=0.8,
                )

    def test_topic_turn_link_unique(self):
        turn = ConversationTurn.objects.create(
            prediction_run=self.run,
            shock_event=self.shock,
            cluster=self.cluster,
            speaker_type=ConversationTurn.SPEAKER_CLUSTER,
            text="This policy feels too opaque.",
        )
        topic = MemoryTopic.objects.create(
            agenda=self.agenda,
            cluster=self.cluster,
            title="Trust and opacity",
        )
        MemoryTopicLink.objects.create(topic=topic, turn=turn)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MemoryTopicLink.objects.create(topic=topic, turn=turn)

