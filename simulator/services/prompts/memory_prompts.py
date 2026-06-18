TOPIC_SELECTION_SYSTEM_INSTRUCTION = (
    "You select memory topics relevant to a social prediction step. "
    "Return strict JSON only. Do not include markdown."
)

TOPIC_UPDATE_SYSTEM_INSTRUCTION = (
    "You update social simulation memory topics from raw turns. "
    "Return strict JSON only. Do not include markdown."
)


def build_topic_selection_prompt(agenda, cluster, shock_event, topic_list):
    return f"""
Agenda:
{agenda.title}
{agenda.description}

Cluster:
{cluster.name if cluster else "global"}
{cluster.description if cluster else ""}

Shock event:
{shock_event.title if shock_event else ""}
{shock_event.description if shock_event else ""}

Available topics:
{topic_list}

Select relevant topic IDs for this response.

Return JSON object:
{{
  "topic_ids": ["..."],
  "reasoning": "short reason"
}}
""".strip()


def build_topic_update_prompt(turn, existing_topics):
    return f"""
New raw turn:
speaker_type: {turn.speaker_type}
text: {turn.text}
payload: {turn.raw_payload}

Existing topics:
{existing_topics}

Decide whether this turn should link to existing topics or create a new topic.

Return JSON object:
{{
  "topics": [
    {{
      "id": "existing topic id or empty for new",
      "title": "topic title",
      "summary": "updated summary",
      "freshness_score": 0.0,
      "importance_score": 0.0,
      "link_reason": "why linked",
      "confidence": 0.0
    }}
  ]
}}
""".strip()

