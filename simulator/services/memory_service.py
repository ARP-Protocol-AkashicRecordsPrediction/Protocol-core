from typing import Iterable, List, Optional

from simulator.models import Agenda, ConversationTurn, MemoryTopic, MemoryTopicLink, PopulationCluster, ShockEvent
from simulator.services.json_service import coerce_float_score, extract_json_object
from simulator.services.llm.factory import get_llm_client
from simulator.services.prompts.memory_prompts import (
    TOPIC_SELECTION_SYSTEM_INSTRUCTION,
    TOPIC_UPDATE_SYSTEM_INSTRUCTION,
    build_topic_selection_prompt,
    build_topic_update_prompt,
)


class MemoryService:
    def __init__(self, llm_client=None) -> None:
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def list_topics_for_context(
        self,
        agenda: Agenda,
        cluster: Optional[PopulationCluster] = None,
    ) -> List[MemoryTopic]:
        query = MemoryTopic.objects.filter(agenda=agenda)
        if cluster is not None:
            query = query.filter(cluster__in=[cluster, None])
        return list(query.order_by("-importance_score", "-freshness_score", "title"))

    def select_relevant_topics(
        self,
        agenda: Agenda,
        cluster: Optional[PopulationCluster],
        shock_event: Optional[ShockEvent],
        topic_list: Iterable[MemoryTopic],
    ) -> List[MemoryTopic]:
        topics = list(topic_list)
        if not topics:
            return []
        prompt = build_topic_selection_prompt(
            agenda=agenda,
            cluster=cluster,
            shock_event=shock_event,
            topic_list=[self._topic_payload(topic) for topic in topics],
        )
        response = self.llm_client.generate(
            prompt=prompt,
            purpose="memory_topic_selection",
            system_instruction=TOPIC_SELECTION_SYSTEM_INSTRUCTION,
        )
        data = extract_json_object(response.text)
        topic_ids = [str(topic_id) for topic_id in data.get("topic_ids", [])]
        return [topic for topic in topics if str(topic.id) in topic_ids]

    def get_raw_turns_for_topics(self, topics: Iterable[MemoryTopic]) -> List[ConversationTurn]:
        topic_ids = [topic.id for topic in topics]
        if not topic_ids:
            return []
        return list(
            ConversationTurn.objects.filter(topic_links__topic_id__in=topic_ids)
            .distinct()
            .order_by("created_at")
        )

    def store_turn_and_update_topics(self, turn: ConversationTurn) -> List[MemoryTopicLink]:
        return self.update_or_create_topics_for_turn(turn)

    def update_or_create_topics_for_turn(self, turn: ConversationTurn) -> List[MemoryTopicLink]:
        agenda = turn.prediction_run.agenda
        existing_topics = self.list_topics_for_context(agenda, turn.cluster)
        prompt = build_topic_update_prompt(
            turn=turn,
            existing_topics=[self._topic_payload(topic) for topic in existing_topics],
        )
        response = self.llm_client.generate(
            prompt=prompt,
            purpose="memory_topic_update",
            system_instruction=TOPIC_UPDATE_SYSTEM_INSTRUCTION,
        )
        data = extract_json_object(response.text)
        links = []
        for item in data.get("topics", []):
            topic = self._resolve_topic(agenda, turn.cluster, item)
            link, _ = MemoryTopicLink.objects.update_or_create(
                topic=topic,
                turn=turn,
                defaults={
                    "link_reason": item.get("link_reason", ""),
                    "confidence": coerce_float_score(item.get("confidence", 0.5), "confidence"),
                },
            )
            links.append(link)
        return links

    def _resolve_topic(self, agenda: Agenda, cluster: Optional[PopulationCluster], item: dict) -> MemoryTopic:
        topic_id = item.get("id")
        if topic_id:
            try:
                topic = MemoryTopic.objects.get(id=topic_id, agenda=agenda)
                topic.title = item.get("title") or topic.title
                topic.summary = item.get("summary") or topic.summary
                topic.freshness_score = coerce_float_score(item.get("freshness_score", topic.freshness_score), "freshness_score")
                topic.importance_score = coerce_float_score(item.get("importance_score", topic.importance_score), "importance_score")
                topic.save()
                return topic
            except MemoryTopic.DoesNotExist:
                pass
        topic, _ = MemoryTopic.objects.update_or_create(
            agenda=agenda,
            cluster=cluster,
            title=item.get("title", "Untitled topic"),
            defaults={
                "summary": item.get("summary", ""),
                "freshness_score": coerce_float_score(item.get("freshness_score", 0.5), "freshness_score"),
                "importance_score": coerce_float_score(item.get("importance_score", 0.5), "importance_score"),
            },
        )
        return topic

    def _topic_payload(self, topic: MemoryTopic) -> dict:
        return {
            "id": str(topic.id),
            "title": topic.title,
            "summary": topic.summary,
            "freshness_score": topic.freshness_score,
            "importance_score": topic.importance_score,
            "cluster_id": str(topic.cluster_id) if topic.cluster_id else None,
        }
