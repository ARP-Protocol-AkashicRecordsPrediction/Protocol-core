from typing import List

from django.utils import timezone

from simulator.models import (
    ClusterState,
    ConversationTurn,
    PersonaInstance,
    PopulationCluster,
    PredictionRun,
    ShockEvent,
)
from simulator.services.aggregation_service import AggregationService
from simulator.services.errors import PredictionStateError
from simulator.services.json_service import coerce_float_score, extract_json_array, extract_json_object, require_keys
from simulator.services.llm.factory import get_llm_client
from simulator.services.memory_service import MemoryService
from simulator.services.prompts.prediction_prompts import (
    CLUSTER_REACTION_SYSTEM_INSTRUCTION,
    PERSONA_SAMPLE_SYSTEM_INSTRUCTION,
    build_cluster_reaction_prompt,
    build_persona_sample_prompt,
)


class PredictionService:
    def __init__(self, llm_client=None, memory_service=None, aggregation_service=None) -> None:
        self._llm_client = llm_client
        self.memory_service = memory_service or MemoryService(llm_client=llm_client)
        self.aggregation_service = aggregation_service or AggregationService()

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def run_prediction(self, prediction_run_id) -> PredictionRun:
        prediction_run = PredictionRun.objects.select_related("agenda").get(id=prediction_run_id)
        if prediction_run.status not in [PredictionRun.STATUS_PENDING, PredictionRun.STATUS_FAILED]:
            raise PredictionStateError("Only pending or failed prediction runs can be started.")
        prediction_run.status = PredictionRun.STATUS_RUNNING
        prediction_run.started_at = timezone.now()
        prediction_run.completed_at = None
        prediction_run.error_message = ""
        prediction_run.save(update_fields=["status", "started_at", "completed_at", "error_message", "updated_at"])
        try:
            for shock_event in prediction_run.shock_events.order_by("order"):
                self.run_shock_step(prediction_run, shock_event)
            distribution = self.aggregation_service.build_opinion_distribution(prediction_run)
            prediction_run.opinion_distribution = distribution
            prediction_run.result_summary = self.aggregation_service.build_result_summary(prediction_run)
            prediction_run.status = PredictionRun.STATUS_COMPLETED
            prediction_run.completed_at = timezone.now()
            prediction_run.save()
            return prediction_run
        except Exception as exc:
            prediction_run.status = PredictionRun.STATUS_FAILED
            prediction_run.error_message = str(exc)
            prediction_run.completed_at = timezone.now()
            prediction_run.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
            raise

    def run_shock_step(self, prediction_run: PredictionRun, shock_event: ShockEvent) -> List[ClusterState]:
        states = []
        clusters = PopulationCluster.objects.filter(agenda=prediction_run.agenda).order_by("name")
        for cluster in clusters:
            state = self.run_cluster_reaction(prediction_run, shock_event, cluster)
            states.append(state)
            self.maybe_expand_persona_samples(cluster, state)
        return states

    def run_cluster_reaction(
        self,
        prediction_run: PredictionRun,
        shock_event: ShockEvent,
        cluster: PopulationCluster,
    ) -> ClusterState:
        topics = self.memory_service.list_topics_for_context(prediction_run.agenda, cluster)
        selected_topics = self.memory_service.select_relevant_topics(prediction_run.agenda, cluster, shock_event, topics)
        raw_turns = self.memory_service.get_raw_turns_for_topics(selected_topics)
        prompt = build_cluster_reaction_prompt(
            agenda=prediction_run.agenda,
            cluster=cluster,
            shock_event=shock_event,
            topic_summaries=[self._topic_summary(topic) for topic in selected_topics],
            raw_turns=[self._turn_payload(turn) for turn in raw_turns],
        )
        response = self.llm_client.generate(
            prompt=prompt,
            purpose="cluster_reaction",
            system_instruction=CLUSTER_REACTION_SYSTEM_INSTRUCTION,
        )
        data = extract_json_object(response.text)
        require_keys(
            data,
            [
                "stance",
                "acceptance_score",
                "behavior_intent",
                "risk_factors",
                "reasoning",
                "confidence",
                "raw_utterance",
            ],
        )
        state, _ = ClusterState.objects.update_or_create(
            prediction_run=prediction_run,
            shock_event=shock_event,
            cluster=cluster,
            defaults={
                "stance": data["stance"],
                "sentiment": data.get("sentiment", ""),
                "acceptance_score": coerce_float_score(data["acceptance_score"], "acceptance_score"),
                "behavior_intent": data.get("behavior_intent", {}),
                "risk_factors": data.get("risk_factors", []),
                "reasoning": data.get("reasoning", ""),
                "confidence": coerce_float_score(data.get("confidence", 0.5), "confidence"),
            },
        )
        turn = ConversationTurn.objects.create(
            prediction_run=prediction_run,
            shock_event=shock_event,
            cluster=cluster,
            speaker_type=ConversationTurn.SPEAKER_CLUSTER,
            text=data.get("raw_utterance", data.get("reasoning", "")),
            raw_payload=data,
        )
        self.memory_service.store_turn_and_update_topics(turn)
        return state

    def maybe_expand_persona_samples(self, cluster: PopulationCluster, cluster_state: ClusterState) -> List[PersonaInstance]:
        config = cluster_state.prediction_run.config or {}
        if not config.get("hybrid_sampling", False):
            return []
        if not self._needs_sampling(cluster_state):
            return []
        max_samples = int(config.get("max_persona_samples_per_cluster", 3))
        existing_count = PersonaInstance.objects.filter(cluster=cluster).count()
        sample_count = max(max_samples - existing_count, 0)
        if sample_count <= 0:
            return []
        prompt = build_persona_sample_prompt(cluster, cluster_state, sample_count)
        response = self.llm_client.generate(
            prompt=prompt,
            purpose="persona_sampling",
            system_instruction=PERSONA_SAMPLE_SYSTEM_INSTRUCTION,
        )
        items = extract_json_array(response.text)
        personas = []
        for item in items[:sample_count]:
            name = item.get("name")
            if not name:
                continue
            persona, _ = PersonaInstance.objects.update_or_create(
                cluster=cluster,
                name=name,
                defaults={"profile": item.get("profile", {})},
            )
            personas.append(persona)
        return personas

    def _needs_sampling(self, cluster_state: ClusterState) -> bool:
        if cluster_state.confidence < 0.55:
            return True
        if 0.4 <= cluster_state.acceptance_score <= 0.6:
            return True
        if len(cluster_state.risk_factors) >= 4 and len(cluster_state.reasoning) < 120:
            return True
        return False

    def _topic_summary(self, topic) -> dict:
        return {
            "id": str(topic.id),
            "title": topic.title,
            "summary": topic.summary,
            "freshness_score": topic.freshness_score,
            "importance_score": topic.importance_score,
        }

    def _turn_payload(self, turn) -> dict:
        return {
            "id": str(turn.id),
            "speaker_type": turn.speaker_type,
            "text": turn.text,
            "raw_payload": turn.raw_payload,
        }
