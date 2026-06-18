CLUSTER_EXPANSION_SYSTEM_INSTRUCTION = (
    "You design population clusters for social prediction simulations. "
    "Return strict JSON only. Do not include markdown."
)


def build_cluster_expansion_prompt(agenda, seed_clusters, desired_count, generation_notes):
    return f"""
Agenda:
- title: {agenda.title}
- description: {agenda.description}
- target_region: {agenda.target_region}
- target_population: {agenda.target_population}

Existing or seed clusters:
{seed_clusters}

Desired total cluster count: {desired_count}
Generation notes: {generation_notes or ""}

Create or complete a diverse set of weighted social population clusters.

Rules:
- Preserve any explicit seed cluster weight exactly.
- If a cluster has no explicit weight, estimate weight and set weight_source to "llm_estimated".
- confidence must be between 0 and 1.
- weight must be non-negative.
- Return a JSON array only.

Each object must include:
name, description, demographics, values, traits, media_diet, pain_points,
weight, weight_source, confidence.
""".strip()

