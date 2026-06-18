CLUSTER_REACTION_SYSTEM_INSTRUCTION = (
    "You simulate a weighted social population cluster reacting to an agenda shock. "
    "Return strict JSON only. Do not include markdown."
)

PERSONA_SAMPLE_SYSTEM_INSTRUCTION = (
    "You create sample personas inside a population cluster for uncertainty testing. "
    "Return strict JSON only. Do not include markdown."
)

FINAL_SUMMARY_SYSTEM_INSTRUCTION = (
    "You summarize weighted social prediction results. Return concise prose."
)


def build_cluster_reaction_prompt(agenda, cluster, shock_event, topic_summaries, raw_turns):
    return f"""
Agenda:
{agenda.title}
{agenda.description}

Target:
- region: {agenda.target_region}
- population: {agenda.target_population}

Population cluster:
- name: {cluster.name}
- description: {cluster.description}
- demographics: {cluster.demographics}
- values: {cluster.values}
- traits: {cluster.traits}
- media_diet: {cluster.media_diet}
- pain_points: {cluster.pain_points}
- weight: {cluster.weight}
- confidence: {cluster.confidence}

Shock event:
- order: {shock_event.order}
- title: {shock_event.title}
- description: {shock_event.description}
- type: {shock_event.event_type}

Relevant topic summaries:
{topic_summaries}

Linked raw memory:
{raw_turns}

Predict this cluster's state after the shock.

Return JSON object:
{{
  "stance": "short stance label",
  "sentiment": "short sentiment label",
  "acceptance_score": 0.0,
  "behavior_intent": {{"primary": "...", "secondary": []}},
  "risk_factors": ["..."],
  "reasoning": "specific rationale grounded in the cluster and memory",
  "confidence": 0.0,
  "raw_utterance": "natural language reaction from this cluster"
}}
""".strip()


def build_persona_sample_prompt(cluster, cluster_state, sample_count):
    return f"""
Cluster:
{cluster.name}
{cluster.description}
demographics: {cluster.demographics}
values: {cluster.values}
traits: {cluster.traits}
media_diet: {cluster.media_diet}
pain_points: {cluster.pain_points}

Uncertain cluster state:
stance: {cluster_state.stance}
acceptance_score: {cluster_state.acceptance_score}
confidence: {cluster_state.confidence}
reasoning: {cluster_state.reasoning}

Create {sample_count} sample personas inside this cluster.
Return JSON array only. Each object must include name and profile.
""".strip()


def build_final_summary_prompt(prediction_run, distribution):
    return f"""
Agenda:
{prediction_run.agenda.title}
{prediction_run.agenda.description}

Weighted opinion distribution:
{distribution}

Write a concise social prediction summary with:
- dominant reaction
- minority reactions
- key risks
- confidence caveats
""".strip()

