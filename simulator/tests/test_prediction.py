import json

from django.test import TestCase

from simulator.models import Agenda, ClusterState, ConversationTurn, PopulationCluster, PredictionRun, ShockEvent
from simulator.services.llm.base import LLMResponse
from simulator.services.prediction_service import PredictionService


class FakePredictionLLM:
    provider = "fake"
    model = "fake-model"

    def generate(self, prompt, purpose, system_instruction=None):
        if purpose == "cluster_reaction":
            return LLMResponse(
                text=json.dumps(
                    {
                        "stance": "skeptical",
                        "sentiment": "concerned",
                        "acceptance_score": 0.25,
                        "behavior_intent": {"primary": "criticize", "secondary": ["wait"]},
                        "risk_factors": ["trust loss"],
                        "reasoning": "This cluster distrusts opaque AI policy.",
                        "confidence": 0.8,
                        "raw_utterance": "This sounds like another opaque AI policy.",
                    }
                ),
                raw={},
                provider=self.provider,
                model=self.model,
            )
        if purpose == "memory_topic_update":
            return LLMResponse(
                text=json.dumps(
                    {
                        "topics": [
                            {
                                "id": "",
                                "title": "AI policy trust",
                                "summary": "Cluster expresses trust concerns.",
                                "freshness_score": 0.9,
                                "importance_score": 0.8,
                                "link_reason": "reaction mentions opacity",
                                "confidence": 0.75,
                            }
                        ]
                    }
                ),
                raw={},
                provider=self.provider,
                model=self.model,
            )
        if purpose == "persona_sampling":
            return LLMResponse(text="[]", raw={}, provider=self.provider, model=self.model)
        return LLMResponse(text="{}", raw={}, provider=self.provider, model=self.model)


class PredictionServiceTests(TestCase):
    def test_prediction_run_creates_state_turn_and_distribution(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        PopulationCluster.objects.create(
            agenda=agenda,
            name="Privacy skeptics",
            description="Concerned about AI.",
            weight=0.4,
            confidence=0.8,
        )
        run = PredictionRun.objects.create(agenda=agenda, config={"hybrid_sampling": False})
        ShockEvent.objects.create(
            prediction_run=run,
            order=1,
            title="Announcement",
            description="Policy announced.",
        )

        service = PredictionService(llm_client=FakePredictionLLM())
        result = service.run_prediction(run.id)

        self.assertEqual(result.status, PredictionRun.STATUS_COMPLETED)
        self.assertEqual(ClusterState.objects.count(), 1)
        self.assertEqual(ConversationTurn.objects.count(), 1)
        self.assertIn("skeptical", result.opinion_distribution["overall"])

    def test_bad_llm_json_marks_run_failed(self):
        class BadLLM(FakePredictionLLM):
            def generate(self, prompt, purpose, system_instruction=None):
                return LLMResponse(text="not json", raw={}, provider="fake", model="fake")

        agenda = Agenda.objects.create(title="Agenda", description="Description")
        PopulationCluster.objects.create(agenda=agenda, name="Cluster")
        run = PredictionRun.objects.create(agenda=agenda)
        ShockEvent.objects.create(
            prediction_run=run,
            order=1,
            title="Shock",
            description="Shock.",
        )

        with self.assertRaises(Exception):
            PredictionService(llm_client=BadLLM()).run_prediction(run.id)

        run.refresh_from_db()
        self.assertEqual(run.status, PredictionRun.STATUS_FAILED)

