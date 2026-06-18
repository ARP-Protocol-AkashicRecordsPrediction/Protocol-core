# Social Prediction Simulator

Django-based API server for simulating social reaction to an agenda across weighted population clusters.

This is not a one-to-one persona chat app. A run starts with an `Agenda`, builds or accepts multiple `PopulationCluster` records, applies ordered `ShockEvent` inputs, and stores cluster-level reactions, weighted opinion distribution, risks, evidence, and topic-linked memory.

## Core Concepts

- `Agenda`: the issue, policy, product, or social narrative to predict.
- `PopulationCluster`: a weighted group with demographics, values, traits, media diet, and pain points.
- `ShockEvent`: an external event injected into a run, such as a policy announcement or public backlash.
- `ClusterState`: a cluster's stance, sentiment, acceptance score, behavior intent, risks, and reasoning after a shock.
- `MemoryTopic`: a topic summary linked to raw `ConversationTurn` records.

## Memory Architecture

The simulator does not keep in-process session memory. Context is retrieved from the database:

1. List topic summaries for the agenda and cluster.
2. Ask the active LLM provider to select relevant topic IDs.
3. Load all raw turns linked to selected topics.
4. Generate the next cluster reaction from persona/cluster data, shock context, topic summaries, and linked raw data.
5. Store new raw turns and update topic links/summaries.

There is no vector database in v1.

## Requirements

- Python 3.9+
- Redis for Celery when running asynchronous prediction tasks
- Gemini or OpenAI API key

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

Edit `.env` with the API key for the provider enabled in `socialsim/settings.py`.

Provider selection is intentionally configured in code:

```python
USE_GEMINI = True   # Gemini
USE_GEMINI = False  # OpenAI
```

## Run

```bash
python manage.py runserver 127.0.0.1:8520
```

Port convention:

- Backend: `8520`
- Frontend, if added later: `3520`

Run Celery in another shell when using `POST /api/prediction-runs/{id}/start/`:

```bash
redis-server
celery -A socialsim worker -l info
```

## API Sketch

Create an agenda:

```bash
curl -sS -X POST http://127.0.0.1:8520/api/agendas/ \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "AI search regulation backlash",
    "description": "Predict public reaction to a new AI search disclosure policy.",
    "target_region": "US",
    "target_population": "general online users"
  }'
```

Expand clusters:

```bash
curl -sS -X POST http://127.0.0.1:8520/api/agendas/<agenda_id>/clusters/expand/ \
  -H 'Content-Type: application/json' \
  -d '{
    "desired_count": 8,
    "generation_notes": "Include creators, policy skeptics, AI power users, privacy-first users.",
    "seed_clusters": [
      {
        "name": "Privacy-first skeptics",
        "description": "Users worried about tracking and opaque AI systems.",
        "weight": 0.22
      }
    ]
  }'
```

Create a prediction run:

```bash
curl -sS -X POST http://127.0.0.1:8520/api/prediction-runs/ \
  -H 'Content-Type: application/json' \
  -d '{
    "agenda_id": "<agenda_id>",
    "config": {
      "hybrid_sampling": true,
      "max_persona_samples_per_cluster": 3
    },
    "shock_events": [
      {
        "order": 1,
        "title": "Policy announcement",
        "description": "Government announces disclosure label requirements.",
        "event_type": "policy"
      }
    ]
  }'
```

Start the run:

```bash
curl -sS -X POST http://127.0.0.1:8520/api/prediction-runs/<run_id>/start/
```

## Tests

```bash
python manage.py test
```

## Operational Notes

- `.env.production` is not used. Keep deployment env files named `.env`.
- LLM fallback responses are intentionally not implemented. Missing keys and provider errors fail clearly.
- SQLite is the default database for v1. PostgreSQL can be added later without changing the domain model.
# Protocol-core
