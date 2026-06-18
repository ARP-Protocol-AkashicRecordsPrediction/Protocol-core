from typing import Any, Dict, Iterable, List, Optional

from simulator.models import Agenda, PopulationCluster
from simulator.services.json_service import extract_json_array, require_keys
from simulator.services.llm.factory import get_llm_client
from simulator.services.prompts.cluster_prompts import (
    CLUSTER_EXPANSION_SYSTEM_INSTRUCTION,
    build_cluster_expansion_prompt,
)


class PopulationService:
    def __init__(self, llm_client=None) -> None:
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def expand_clusters_for_agenda(
        self,
        agenda: Agenda,
        seed_clusters: Optional[Iterable[Dict[str, Any]]] = None,
        desired_count: int = 8,
        generation_notes: str = "",
    ) -> List[PopulationCluster]:
        saved = self.merge_seed_clusters(agenda, seed_clusters or [])
        remaining = max(desired_count - len(saved), 0)
        if remaining:
            saved.extend(
                self.create_llm_estimated_clusters(
                    agenda=agenda,
                    desired_count=remaining,
                    generation_notes=generation_notes,
                    seed_clusters=seed_clusters or [],
                )
            )
        return list(PopulationCluster.objects.filter(agenda=agenda).order_by("name"))

    def merge_seed_clusters(
        self,
        agenda: Agenda,
        seed_clusters: Iterable[Dict[str, Any]],
    ) -> List[PopulationCluster]:
        saved = []
        for seed in seed_clusters:
            name = seed.get("name")
            if not name:
                continue
            has_weight = "weight" in seed and seed.get("weight") is not None
            defaults = {
                "description": seed.get("description", ""),
                "demographics": seed.get("demographics", {}),
                "values": seed.get("values", {}),
                "traits": seed.get("traits", {}),
                "media_diet": seed.get("media_diet", []),
                "pain_points": seed.get("pain_points", []),
                "weight": float(seed.get("weight", 1.0)),
                "weight_source": PopulationCluster.WEIGHT_EXPLICIT
                if has_weight
                else PopulationCluster.WEIGHT_EQUAL_DEFAULT,
                "confidence": float(seed.get("confidence", 0.75 if has_weight else 0.5)),
            }
            cluster, _ = PopulationCluster.objects.update_or_create(
                agenda=agenda,
                name=name,
                defaults=defaults,
            )
            saved.append(cluster)
        return saved

    def create_llm_estimated_clusters(
        self,
        agenda: Agenda,
        desired_count: int,
        generation_notes: str = "",
        seed_clusters: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> List[PopulationCluster]:
        prompt = build_cluster_expansion_prompt(
            agenda=agenda,
            seed_clusters=list(seed_clusters or []),
            desired_count=desired_count,
            generation_notes=generation_notes,
        )
        response = self.llm_client.generate(
            prompt=prompt,
            purpose="cluster_expansion",
            system_instruction=CLUSTER_EXPANSION_SYSTEM_INSTRUCTION,
        )
        cluster_items = extract_json_array(response.text)
        saved = []
        for item in cluster_items[:desired_count]:
            require_keys(
                item,
                [
                    "name",
                    "description",
                    "demographics",
                    "values",
                    "traits",
                    "media_diet",
                    "pain_points",
                    "weight",
                    "confidence",
                ],
            )
            cluster, _ = PopulationCluster.objects.update_or_create(
                agenda=agenda,
                name=item["name"],
                defaults={
                    "description": item.get("description", ""),
                    "demographics": item.get("demographics", {}),
                    "values": item.get("values", {}),
                    "traits": item.get("traits", {}),
                    "media_diet": item.get("media_diet", []),
                    "pain_points": item.get("pain_points", []),
                    "weight": float(item.get("weight", 1.0)),
                    "weight_source": item.get("weight_source") or PopulationCluster.WEIGHT_LLM_ESTIMATED,
                    "confidence": float(item.get("confidence", 0.5)),
                },
            )
            saved.append(cluster)
        return saved
