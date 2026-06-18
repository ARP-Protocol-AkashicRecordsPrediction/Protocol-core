from collections import Counter, defaultdict
from typing import Dict, List

from simulator.models import ClusterState, PredictionRun


class AggregationService:
    def build_opinion_distribution(self, prediction_run: PredictionRun) -> Dict[str, object]:
        states = list(
            ClusterState.objects.select_related("cluster", "shock_event")
            .filter(prediction_run=prediction_run)
            .order_by("shock_event__order", "cluster__name")
        )
        latest_by_cluster = {}
        for state in states:
            latest_by_cluster[state.cluster_id] = state
        latest_states = list(latest_by_cluster.values())
        total_latest_weight = sum(state.cluster.weight for state in latest_states) or 1.0
        by_stance = defaultdict(float)
        by_shock = defaultdict(lambda: defaultdict(float))
        shock_totals = defaultdict(float)
        by_cluster = []
        for state in states:
            shock_totals[str(state.shock_event.order)] += state.cluster.weight
        for state in latest_states:
            by_stance[state.stance] += state.cluster.weight / total_latest_weight
        for state in states:
            shock_order = str(state.shock_event.order)
            normalized_shock_weight = state.cluster.weight / (shock_totals[shock_order] or 1.0)
            by_shock[shock_order][state.stance] += normalized_shock_weight
            by_cluster.append(
                {
                    "cluster_id": str(state.cluster_id),
                    "cluster": state.cluster.name,
                    "shock_order": state.shock_event.order,
                    "stance": state.stance,
                    "acceptance_score": state.acceptance_score,
                    "weight": state.cluster.weight,
                    "confidence": state.confidence,
                }
            )
        return {
            "overall": dict(by_stance),
            "by_shock": {order: dict(values) for order, values in by_shock.items()},
            "by_cluster": by_cluster,
            "top_risks": self.collect_risk_factors(prediction_run),
            "behavior_intent": self.summarize_behavior_intent(prediction_run),
        }

    def summarize_behavior_intent(self, prediction_run: PredictionRun) -> Dict[str, int]:
        counter = Counter()
        states = ClusterState.objects.filter(prediction_run=prediction_run)
        for state in states:
            primary = state.behavior_intent.get("primary")
            if primary:
                counter[primary] += 1
        return dict(counter)

    def collect_risk_factors(self, prediction_run: PredictionRun) -> List[dict]:
        counter = Counter()
        states = ClusterState.objects.filter(prediction_run=prediction_run).select_related("cluster")
        for state in states:
            for risk in state.risk_factors:
                counter[str(risk)] += 1
        return [{"risk": risk, "count": count} for risk, count in counter.most_common(10)]

    def build_result_summary(self, prediction_run: PredictionRun) -> str:
        distribution = prediction_run.opinion_distribution or {}
        overall = distribution.get("overall", {})
        if not overall:
            return "No cluster states were generated."
        dominant = max(overall.items(), key=lambda item: item[1])
        return (
            f"Dominant stance is '{dominant[0]}' with weighted share {dominant[1]:.2f}. "
            f"Top risks: {distribution.get('top_risks', [])[:3]}"
        )
