import json

from django.test import TestCase

from simulator.models import Agenda, ConversationTurn, MemoryTopic, MemoryTopicLink, PopulationCluster, PredictionRun, ShockEvent
from simulator.services.llm.base import LLMResponse
from simulator.services.memory_service import MemoryService


class FakeLLM:
    provider = "fake"
    model = "fake-model"

    def generate(self, prompt, purpose, system_instruction=None):
        if purpose == "memory_topic_selection":
            return LLMResponse(
                text=json.dumps({"topic_ids": [str(self.topic_id)], "reasoning": "relevant"}),
                raw={},
                provider=self.provider,
                model=self.model,
            )
        return LLMResponse(
            text=json.dumps(
                {
                    "topics": [
                        {
                            "id": "",
                            "title": "Trust",
                            "summary": "Trust concerns emerged.",
                            "freshness_score": 0.8,
                            "importance_score": 0.9,
                            "link_reason": "mentions trust",
                            "confidence": 0.7,
                        }
                    ]
                }
            ),
            raw={},
            provider=self.provider,
            model=self.model,
        )


class MemoryServiceTests(TestCase):
    def setUp(self):
        self.agenda = Agenda.objects.create(title="Agenda", description="Description")
        self.cluster = PopulationCluster.objects.create(agenda=self.agenda, name="Cluster")
        self.run = PredictionRun.objects.create(agenda=self.agenda)
        self.shock = ShockEvent.objects.create(
            prediction_run=self.run,
            order=1,
            title="Shock",
            description="Shock description.",
        )
        self.turn = ConversationTurn.objects.create(
            prediction_run=self.run,
            shock_event=self.shock,
            cluster=self.cluster,
            speaker_type=ConversationTurn.SPEAKER_CLUSTER,
            text="Trust is the central issue.",
        )

    def test_selected_topic_loads_all_linked_raw_turns(self):
        topic = MemoryTopic.objects.create(agenda=self.agenda, cluster=self.cluster, title="Trust")
        MemoryTopicLink.objects.create(topic=topic, turn=self.turn)
        fake = FakeLLM()
        fake.topic_id = topic.id
        service = MemoryService(llm_client=fake)

        selected = service.select_relevant_topics(self.agenda, self.cluster, self.shock, [topic])
        raw_turns = service.get_raw_turns_for_topics(selected)

        self.assertEqual(selected, [topic])
        self.assertEqual(raw_turns, [self.turn])

    def test_store_turn_creates_topic_link(self):
        fake = FakeLLM()
        fake.topic_id = "unused"
        service = MemoryService(llm_client=fake)

        links = service.store_turn_and_update_topics(self.turn)

        self.assertEqual(len(links), 1)
        self.assertEqual(MemoryTopic.objects.count(), 1)
        self.assertEqual(MemoryTopicLink.objects.count(), 1)

