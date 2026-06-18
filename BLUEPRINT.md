# Social Prediction Simulator Blueprint

이 문서는 구현 코드가 아니라, 구현 전에 합의할 서버 설계 청사진이다.
목표는 Django 기반 Social Prediction Simulator를 파일 단위로 쪼개서, 다음 턴에 그대로 구현 가능한 수준까지 정의하는 것이다.

## 0. Product Intent

이 프로젝트는 `persona <> persona` 1:1 대화기가 아니다.

하나의 `Agenda`에 대해 서로 다른 성향, 인구 특성, 가치관, 미디어 소비 패턴을 가진 `PopulationCluster`들이 외부 충격 `ShockEvent`에 따라 어떻게 입장과 행동 의도를 바꾸는지 예측한다.

핵심 결과는 다음이다.

- 군집별 반응 근거
- shock 단계별 입장 변화
- weight 기반 전체 의견 분포
- 행동 의도와 리스크 요인
- 토픽별 요약 메모리와 raw data 링크

## 1. Non-Negotiable Rules

- v1은 인증 없는 로컬/오픈소스 API 서버로 간다.
- Next.js frontend는 만들거나 실행하지 않는다.
- Port convention is backend `8520`, frontend `3520` if a separate frontend is added later.
- `.env.production`은 사용하지 않는다. 환경 파일 이름은 `.env`로 통일한다.
- 동작 설정은 최대한 `settings.py`에 둔다. `.env`는 secret/API key 중심으로만 사용한다.
- LLM fallback은 만들지 않는다. API key 누락, provider 오류, JSON 파싱 실패는 명확히 실패시킨다.
- 세션 메모리 객체는 사용하지 않는다. 모든 기억은 DB의 `MemoryTopic`, `MemoryTopicLink`, `ConversationTurn`에서 회수한다.
- Ubuntu 배포/업데이트 전에는 git commit을 먼저 만든다는 운영 규칙을 문서화한다.

## 2. Planned Server Tree

```text
UXSimulator/
├── AGENTS.md
├── BLUEPRINT.md
├── README.md
├── requirements.txt
├── .env.example
├── manage.py
├── socialsim/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
└── simulator/
    ├── __init__.py
    ├── apps.py
    ├── admin.py
    ├── models.py
    ├── serializers.py
    ├── urls.py
    ├── views.py
    ├── tasks.py
    ├── migrations/
    │   └── __init__.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_api.py
    │   ├── test_memory.py
    │   └── test_prediction.py
    └── services/
        ├── __init__.py
        ├── errors.py
        ├── json_service.py
        ├── population_service.py
        ├── memory_service.py
        ├── prediction_service.py
        ├── aggregation_service.py
        ├── llm/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── gemini.py
        │   ├── openai.py
        │   └── factory.py
        └── prompts/
            ├── __init__.py
            ├── cluster_prompts.py
            ├── memory_prompts.py
            └── prediction_prompts.py
```

## 3. Root Files

### `AGENTS.md`

Purpose:
- 이 저장소에서 Codex/agent가 지켜야 할 작업 규칙을 명시한다.

Content:
- `.env.production` 금지, `.env` 통일
- 설정값을 env 변수로 과하게 빼지 말 것
- Ubuntu 업데이트 전 git commit
- fallback 지양
- Next.js frontend port 열지 않기
- 기존 사용자 변경 revert 금지
- 구현 전 blueprint 확인 규칙

### `README.md`

Purpose:
- 오픈소스 사용자가 서버를 이해하고 실행할 수 있는 문서.

Sections:
- 프로젝트 소개
- Social Prediction 개념 설명
- Memory architecture 설명
- 설치
- `.env` 작성
- migration
- Redis/Celery 실행
- Django API 서버 실행
- API 사용 예제
- LLM provider 전환 방법
- 테스트 실행
- 개발 로드맵

Must mention:
- v1은 auth 없음
- SQLite 기본
- PostgreSQL 전환 가능
- vector DB 없음
- fallback 없음

### `requirements.txt`

Purpose:
- Python dependency 정의.

Expected packages:
- `Django`
- `djangorestframework`
- `python-dotenv`
- `celery`
- `redis`
- `google-genai`
- `openai`
- `orjson`

Notes:
- `pytest`를 쓸지 Django 기본 test runner만 쓸지는 구현 시 결정한다.
- v1에서는 dependency를 적게 유지한다.

### `.env.example`

Purpose:
- secret/API key 예시.

Allowed variables:
- `SECRET_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`

Avoid:
- `USE_GEMINI`
- `DEBUG`
- `DATABASE_URL`
- `CELERY_BROKER_URL`

Reason:
- 사용자가 요청한 대로 설정값을 env 변수로 과하게 분리하지 않는다.

### `manage.py`

Purpose:
- 표준 Django command entrypoint.

Content:
- `DJANGO_SETTINGS_MODULE = "socialsim.settings"`
- Django 기본 `execute_from_command_line`

## 4. `socialsim/` Project Files

### `socialsim/__init__.py`

Purpose:
- Celery app 로딩.

Content:
- `from .celery import app as celery_app`
- `__all__ = ("celery_app",)`

### `socialsim/settings.py`

Purpose:
- Django 전체 설정.

Key settings:
- `BASE_DIR`
- `SECRET_KEY`는 `.env`에서 읽음
- `DEBUG = True`를 v1 local default로 명시
- `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]`
- `INSTALLED_APPS`
  - Django 기본 앱
  - `rest_framework`
  - `simulator`
- `DATABASES`
  - SQLite 기본
- `REST_FRAMEWORK`
  - 인증 기본값 없음
  - JSON renderer/parser 중심
- `LANGUAGE_CODE = "ko-kr"`
- `TIME_ZONE = "Asia/Seoul"`
- `USE_GEMINI = True`
- `GEMINI_MODEL`
- `OPENAI_MODEL`
- `CELERY_BROKER_URL = "redis://localhost:6379/0"`
- `CELERY_RESULT_BACKEND = "redis://localhost:6379/1"`
- `CELERY_TASK_ALWAYS_EAGER = False`

Important:
- provider 선택은 `.env`가 아니라 `USE_GEMINI` 상수로 전환한다.
- API key는 `.env`에서 읽되, 없으면 client 호출 시 명확히 실패한다.
- fallback text generation은 금지한다.

### `socialsim/urls.py`

Purpose:
- Django root URL routing.

Routes:
- `admin/`
- `api/health/`
- `api/` include `simulator.urls`

Health response:
- `status`
- `service`
- `version`

### `socialsim/asgi.py`

Purpose:
- ASGI entrypoint.

Content:
- 표준 Django ASGI application.

### `socialsim/wsgi.py`

Purpose:
- WSGI entrypoint.

Content:
- 표준 Django WSGI application.

### `socialsim/celery.py`

Purpose:
- Celery app 구성.

Content:
- `DJANGO_SETTINGS_MODULE`
- `app = Celery("socialsim")`
- `app.config_from_object("django.conf:settings", namespace="CELERY")`
- `app.autodiscover_tasks()`

## 5. `simulator/models.py`

Purpose:
- Social prediction domain schema 정의.

Shared abstract model:
- `TimestampedModel`
  - `created_at`
  - `updated_at`

### `Agenda`

Fields:
- `id`: UUID primary key
- `title`: CharField
- `description`: TextField
- `target_region`: CharField blank
- `target_population`: TextField blank
- `metadata`: JSONField default dict
- timestamps

Relationships:
- has many `PopulationCluster`
- has many `PredictionRun`
- has many `MemoryTopic`

Indexes:
- `created_at`
- `title`

### `PopulationCluster`

Fields:
- `id`: UUID primary key
- `agenda`: FK `Agenda`, related name `clusters`
- `name`: CharField
- `description`: TextField
- `demographics`: JSONField default dict
- `values`: JSONField default dict
- `traits`: JSONField default dict
- `media_diet`: JSONField default list
- `pain_points`: JSONField default list
- `weight`: DecimalField or FloatField
- `weight_source`: choices `explicit`, `llm_estimated`, `equal_default`
- `confidence`: FloatField
- timestamps

Rules:
- `weight`는 0 이상.
- `confidence`는 0~1.
- aggregation에서 weight normalization을 수행하므로 DB가 반드시 합계 1을 강제하지는 않는다.

Indexes:
- `(agenda, name)`
- `(agenda, weight)`

### `PersonaInstance`

Fields:
- `id`: UUID primary key
- `cluster`: FK `PopulationCluster`, related name `personas`
- `name`: CharField
- `profile`: JSONField default dict
- `current_memory_summary`: TextField blank
- `recent_memory_summary`: TextField blank
- timestamps

Use:
- 하이브리드 모드에서 불확실성이 높은 cluster를 세분화할 때만 생성한다.

### `PredictionRun`

Fields:
- `id`: UUID primary key
- `agenda`: FK `Agenda`, related name `prediction_runs`
- `status`: choices `pending`, `running`, `completed`, `failed`
- `config`: JSONField default dict
- `result_summary`: TextField blank
- `opinion_distribution`: JSONField default dict
- `started_at`: DateTime null
- `completed_at`: DateTime null
- `error_message`: TextField blank
- timestamps

Use:
- 한 번의 예측 실행 전체를 대표한다.

### `ShockEvent`

Fields:
- `id`: UUID primary key
- `prediction_run`: FK `PredictionRun`, related name `shock_events`
- `order`: PositiveIntegerField
- `title`: CharField
- `description`: TextField
- `event_type`: CharField blank
- `metadata`: JSONField default dict
- timestamps

Rules:
- `(prediction_run, order)` unique.
- run 내부에서는 `order` 오름차순으로 처리한다.

### `ClusterState`

Fields:
- `id`: UUID primary key
- `prediction_run`: FK `PredictionRun`, related name `cluster_states`
- `shock_event`: FK `ShockEvent`, related name `cluster_states`
- `cluster`: FK `PopulationCluster`, related name `states`
- `stance`: CharField
- `sentiment`: CharField
- `acceptance_score`: FloatField
- `behavior_intent`: JSONField default dict
- `risk_factors`: JSONField default list
- `reasoning`: TextField
- `confidence`: FloatField
- timestamps

Rules:
- `(prediction_run, shock_event, cluster)` unique.
- `acceptance_score`는 0~1.

### `ConversationTurn`

Fields:
- `id`: UUID primary key
- `prediction_run`: FK `PredictionRun`, related name `turns`
- `shock_event`: FK `ShockEvent`, null, related name `turns`
- `cluster`: FK `PopulationCluster`, null, related name `turns`
- `persona_instance`: FK `PersonaInstance`, null, related name `turns`
- `speaker_type`: choices `cluster`, `persona`, `system`, `aggregator`
- `text`: TextField
- `raw_payload`: JSONField default dict
- timestamps

Use:
- LLM 응답 원문, reasoning, structured JSON, intermediate result를 raw data로 보존한다.

### `MemoryTopic`

Fields:
- `id`: UUID primary key
- `agenda`: FK `Agenda`, related name `memory_topics`
- `cluster`: FK `PopulationCluster`, null, related name `memory_topics`
- `title`: CharField
- `summary`: TextField
- `freshness_score`: FloatField
- `importance_score`: FloatField
- timestamps

Use:
- 스크린샷의 `토픽별 요약`.
- LLM 호출 전 topic list로 제공된다.

### `MemoryTopicLink`

Fields:
- `id`: UUID primary key
- `topic`: FK `MemoryTopic`, related name `links`
- `turn`: FK `ConversationTurn`, related name `topic_links`
- `link_reason`: TextField blank
- `confidence`: FloatField
- timestamps

Rules:
- `(topic, turn)` unique.

Use:
- topic에서 raw data 전체를 조회하기 위한 링크.

### `LLMCallLog`

Fields:
- `id`: UUID primary key
- `provider`: choices `gemini`, `openai`
- `model`: CharField
- `purpose`: CharField
- `prompt_hash`: CharField
- `request_payload`: JSONField default dict
- `response_payload`: JSONField default dict
- `status`: choices `success`, `failed`
- `error_message`: TextField blank
- timestamps

Use:
- 재현성과 디버깅.
- prompt 전문 저장 여부는 구현 시 token/privacy 비용을 고려하되, v1에서는 payload에 저장한다.

## 6. `simulator/admin.py`

Purpose:
- Django admin에서 모든 주요 객체를 확인 가능하게 한다.

Registrations:
- `AgendaAdmin`
- `PopulationClusterAdmin`
- `PersonaInstanceAdmin`
- `PredictionRunAdmin`
- `ShockEventAdmin`
- `ClusterStateAdmin`
- `ConversationTurnAdmin`
- `MemoryTopicAdmin`
- `MemoryTopicLinkAdmin`
- `LLMCallLogAdmin`

Admin list fields:
- `Agenda`: title, target_region, created_at
- `PopulationCluster`: agenda, name, weight, weight_source, confidence
- `PredictionRun`: agenda, status, started_at, completed_at
- `ShockEvent`: prediction_run, order, title
- `ClusterState`: prediction_run, shock_event, cluster, stance, acceptance_score
- `LLMCallLog`: provider, model, purpose, status, created_at

## 7. `simulator/serializers.py`

Purpose:
- DRF request/response schema.

Serializers:
- `AgendaSerializer`
- `PopulationClusterSerializer`
- `PersonaInstanceSerializer`
- `ShockEventSerializer`
- `PredictionRunSerializer`
- `PredictionRunCreateSerializer`
- `ClusterStateSerializer`
- `ConversationTurnSerializer`
- `MemoryTopicSerializer`
- `MemoryTopicLinkSerializer`
- `ExpandClustersRequestSerializer`
- `StartPredictionRunSerializer`

Important request shapes:

`PredictionRunCreateSerializer`:
- input:
  - `agenda_id`
  - `config`
  - `shock_events`
- behavior:
  - creates `PredictionRun`
  - creates child `ShockEvent` rows

`ExpandClustersRequestSerializer`:
- input:
  - `seed_clusters`
  - `desired_count`
  - `generation_notes`
- output:
  - created/updated clusters

Validation:
- `desired_count` min 1 max 30.
- shock event order must be unique.
- acceptance/confidence scores must be 0~1.

## 8. `simulator/urls.py`

Purpose:
- App-level URL routing.

Routes:
- `api/agendas/`
- `api/clusters/`
- `api/personas/`
- `api/prediction-runs/`
- `api/topics/`

Router:
- DRF `DefaultRouter`
- ViewSets:
  - `AgendaViewSet`
  - `PopulationClusterViewSet`
  - `PersonaInstanceViewSet`
  - `PredictionRunViewSet`
  - `MemoryTopicViewSet`

Extra paths:
- `GET prediction-runs/<uuid:pk>/states/`
- `GET prediction-runs/<uuid:pk>/turns/`

## 9. `simulator/views.py`

Purpose:
- API endpoint orchestration only.
- 비즈니스 로직은 services로 위임한다.

### `AgendaViewSet`

Actions:
- `create`
- `list`
- `retrieve`
- `update`
- `partial_update`
- `destroy`

Extra action:
- `POST /api/agendas/{id}/clusters/expand/`

Calls:
- `PopulationService.expand_clusters_for_agenda`

### `PopulationClusterViewSet`

Actions:
- standard CRUD

Query params:
- `agenda_id`

Behavior:
- agenda별 cluster list filtering.

### `PersonaInstanceViewSet`

Actions:
- standard CRUD

Query params:
- `cluster_id`

Behavior:
- hybrid sampling 결과 확인 및 수동 생성 지원.

### `PredictionRunViewSet`

Actions:
- `create`
- `list`
- `retrieve`
- `destroy`

Extra action:
- `POST /api/prediction-runs/{id}/start/`
  - Celery task enqueue
  - status가 `pending`인 run만 시작
- `GET /api/prediction-runs/{id}/states/`
  - `ClusterState` list
- `GET /api/prediction-runs/{id}/turns/`
  - `ConversationTurn` list

### `MemoryTopicViewSet`

Actions:
- `list`
- `retrieve`

Query params:
- `agenda_id`
- `cluster_id`

Behavior:
- topic summary와 linked raw turn id 목록을 반환.

Error handling:
- service exceptions를 DRF `400` 또는 `500`으로 변환.
- LLM provider 오류는 숨기지 않고 message 반환.

## 10. `simulator/tasks.py`

Purpose:
- Celery task entrypoints.

Tasks:
- `run_prediction_task(prediction_run_id)`

Behavior:
- `PredictionService.run_prediction(prediction_run_id)` 호출.
- task 자체는 얇게 유지.
- 예외 발생 시 `PredictionRun.status = failed`, `error_message` 저장.

Testing mode:
- Django tests에서는 `CELERY_TASK_ALWAYS_EAGER = True` override.

## 11. Services

### `simulator/services/errors.py`

Purpose:
- domain-specific exception 정의.

Classes:
- `SimulatorError`
- `LLMConfigurationError`
- `LLMProviderError`
- `LLMJSONParseError`
- `PredictionStateError`
- `MemoryRetrievalError`

Rules:
- fallback 대신 exception을 올린다.
- views에서 HTTP response로 변환한다.

### `simulator/services/json_service.py`

Purpose:
- LLM JSON 응답 파싱과 validation.

Functions:
- `extract_json_object(text: str) -> dict`
- `extract_json_array(text: str) -> list`
- `require_keys(data: dict, keys: list[str]) -> None`
- `coerce_float_score(value, field_name: str) -> float`

Behavior:
- markdown code fence 제거는 허용.
- JSON이 없으면 `LLMJSONParseError`.
- schema와 맞지 않으면 fallback하지 않고 실패.

### `simulator/services/llm/base.py`

Purpose:
- 공통 LLM client 인터페이스.

Definitions:
- `LLMResponse`
  - `text`
  - `raw`
  - `provider`
  - `model`
- `BaseLLMClient`
  - `generate(prompt: str, purpose: str, system_instruction: str | None = None) -> LLMResponse`

Rules:
- base class는 retry/fallback을 구현하지 않는다.
- logging은 각 provider 또는 wrapper에서 처리한다.

### `simulator/services/llm/gemini.py`

Purpose:
- Google Gemini adapter.

Class:
- `GeminiLLMClient`

Behavior:
- `settings.GEMINI_API_KEY` 없으면 `LLMConfigurationError`.
- `settings.GEMINI_MODEL` 사용.
- `google-genai` client 호출.
- response raw payload 반환.
- 실패 시 `LLMProviderError`.

### `simulator/services/llm/openai.py`

Purpose:
- OpenAI adapter.

Class:
- `OpenAILLMClient`

Behavior:
- `settings.OPENAI_API_KEY` 없으면 `LLMConfigurationError`.
- `settings.OPENAI_MODEL` 사용.
- OpenAI Responses API 또는 chat-compatible call 중 하나로 구현.
- 실패 시 `LLMProviderError`.

Implementation note:
- OpenAI API 최신 사용법은 구현 직전에 공식 문서 기준으로 확인한다.

### `simulator/services/llm/factory.py`

Purpose:
- provider 선택.

Functions:
- `get_llm_client() -> BaseLLMClient`
- `get_provider_name() -> str`

Rules:
- `settings.USE_GEMINI is True`이면 Gemini.
- `False`이면 OpenAI.
- env var로 provider를 바꾸지 않는다.

### `simulator/services/prompts/cluster_prompts.py`

Purpose:
- population cluster 확장 prompt.

Functions/constants:
- `BUILD_CLUSTER_EXPANSION_PROMPT`
- `CLUSTER_EXPANSION_SYSTEM_INSTRUCTION`

Prompt output schema:
- JSON array of clusters:
  - `name`
  - `description`
  - `demographics`
  - `values`
  - `traits`
  - `media_diet`
  - `pain_points`
  - `weight`
  - `weight_source`
  - `confidence`

Rules:
- 입력 weight가 있으면 유지하라는 instruction 포함.
- weight가 없으면 추정값과 confidence를 명시하게 한다.

### `simulator/services/prompts/memory_prompts.py`

Purpose:
- topic 선택, topic 생성/요약 prompt.

Prompts:
- `TOPIC_SELECTION_PROMPT`
- `TOPIC_UPDATE_PROMPT`
- `TOPIC_CREATE_PROMPT`

Topic selection output:
- JSON object:
  - `topic_ids`: list
  - `reasoning`: string

Topic update output:
- JSON object:
  - `summary`
  - `freshness_score`
  - `importance_score`
  - `link_reason`
  - `confidence`

### `simulator/services/prompts/prediction_prompts.py`

Purpose:
- shock별 cluster state 예측 prompt.

Prompts:
- `CLUSTER_REACTION_PROMPT`
- `PERSONA_SAMPLE_PROMPT`
- `FINAL_SUMMARY_PROMPT`

Cluster reaction output:
- JSON object:
  - `stance`
  - `sentiment`
  - `acceptance_score`
  - `behavior_intent`
  - `risk_factors`
  - `reasoning`
  - `confidence`
  - `raw_utterance`

### `simulator/services/population_service.py`

Purpose:
- agenda 기반 사회 군집 생성/보강.

Class:
- `PopulationService`

Methods:
- `expand_clusters_for_agenda(agenda, seed_clusters, desired_count, generation_notes) -> list[PopulationCluster]`
- `merge_seed_clusters(agenda, seed_clusters) -> list[PopulationCluster]`
- `create_llm_estimated_clusters(agenda, desired_count, generation_notes) -> list[PopulationCluster]`

Rules:
- seed cluster에 weight가 있으면 `weight_source = explicit`.
- seed cluster에 weight가 없으면 LLM 추정 또는 equal default.
- 동일 name cluster는 update, 신규 name은 create.
- LLM JSON parse 실패는 실패로 둔다.

### `simulator/services/memory_service.py`

Purpose:
- topic memory retrieval/update.

Class:
- `MemoryService`

Methods:
- `list_topics_for_context(agenda, cluster=None) -> list[MemoryTopic]`
- `select_relevant_topics(agenda, cluster, shock_event, topic_list) -> list[MemoryTopic]`
- `get_raw_turns_for_topics(topics) -> list[ConversationTurn]`
- `store_turn_and_update_topics(turn) -> None`
- `update_or_create_topics_for_turn(turn) -> list[MemoryTopicLink]`

Retrieval flow:
1. LLM에게 topic list 제공.
2. LLM이 관련 topic id 선택.
3. 선택 topic의 linked raw turns 전체 조회.
4. prediction prompt에 raw turns 전체 제공.

Rules:
- vector DB 없음.
- 최근 n턴 session memory 없음.
- topic이 없으면 raw context 없이 진행하되, 그 사실을 prompt에 명시.

### `simulator/services/prediction_service.py`

Purpose:
- 전체 prediction run orchestration.

Class:
- `PredictionService`

Methods:
- `run_prediction(prediction_run_id) -> PredictionRun`
- `run_shock_step(prediction_run, shock_event) -> list[ClusterState]`
- `run_cluster_reaction(prediction_run, shock_event, cluster) -> ClusterState`
- `maybe_expand_persona_samples(cluster, cluster_state) -> list[PersonaInstance]`

Flow:
1. `PredictionRun.status = running`
2. shock events를 order 순회
3. 각 cluster별 topic retrieval
4. cluster reaction LLM 호출
5. `ConversationTurn` 저장
6. `ClusterState` 저장
7. memory topic link/update
8. uncertainty가 높으면 persona samples 생성 및 보조 시뮬레이션
9. aggregation 실행
10. `PredictionRun.status = completed`

Uncertainty heuristic:
- `confidence < 0.55`
- 또는 `acceptance_score`가 0.4~0.6 사이
- 또는 risk factor 수가 많은데 reasoning이 짧음

### `simulator/services/aggregation_service.py`

Purpose:
- weighted social prediction result 계산.

Class:
- `AggregationService`

Methods:
- `build_opinion_distribution(prediction_run) -> dict`
- `summarize_behavior_intent(prediction_run) -> dict`
- `collect_risk_factors(prediction_run) -> list[dict]`
- `build_result_summary(prediction_run) -> str`

Opinion distribution:
- cluster weight normalize
- stance별 weighted share 계산
- shock 단계별 distribution 계산

Output shape:
- `overall`
- `by_shock`
- `by_cluster`
- `top_risks`
- `evidence`

## 12. Tests

### `simulator/tests/test_models.py`

Cases:
- agenda 생성
- cluster weight/confidence 저장
- shock order uniqueness
- cluster state uniqueness
- memory topic link uniqueness

### `simulator/tests/test_api.py`

Cases:
- agenda CRUD
- cluster CRUD
- prediction run 생성 시 shock events 저장
- start action이 pending run만 받는지 확인
- topics list filtering

### `simulator/tests/test_memory.py`

Cases:
- topic list 생성
- selected topics의 raw turns 전체 조회
- topic link 생성
- topic 없을 때도 fallback 없이 빈 context로 처리

### `simulator/tests/test_prediction.py`

Cases:
- fake LLM client로 shock 순회
- cluster state 생성
- conversation turn 저장
- aggregation result 저장
- LLM JSON 실패 시 run failed 처리

## 13. API Contract Draft

### Create Agenda

`POST /api/agendas/`

Request:

```json
{
  "title": "AI search regulation backlash",
  "description": "Predict public reaction to a new AI search disclosure policy.",
  "target_region": "US",
  "target_population": "general online users"
}
```

Response:

```json
{
  "id": "...",
  "title": "...",
  "description": "...",
  "target_region": "US",
  "target_population": "general online users"
}
```

### Expand Clusters

`POST /api/agendas/{agenda_id}/clusters/expand/`

Request:

```json
{
  "desired_count": 8,
  "generation_notes": "Include creators, policy skeptics, AI power users, privacy-first users.",
  "seed_clusters": [
    {
      "name": "Privacy-first skeptics",
      "description": "Users worried about tracking and opaque AI systems.",
      "weight": 0.22
    }
  ]
}
```

Response:

```json
{
  "clusters": [
    {
      "id": "...",
      "name": "Privacy-first skeptics",
      "weight": 0.22,
      "weight_source": "explicit",
      "confidence": 0.85
    }
  ]
}
```

### Create Prediction Run

`POST /api/prediction-runs/`

Request:

```json
{
  "agenda_id": "...",
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
    },
    {
      "order": 2,
      "title": "Influencer criticism",
      "description": "Major creators claim the policy suppresses content.",
      "event_type": "social_reaction"
    }
  ]
}
```

### Start Prediction Run

`POST /api/prediction-runs/{run_id}/start/`

Response:

```json
{
  "id": "...",
  "status": "running"
}
```

### Retrieve Prediction Run

`GET /api/prediction-runs/{run_id}/`

Response includes:
- status
- result_summary
- opinion_distribution
- shock event count
- state count

## 14. Implementation WBS

### Phase 1. Blueprint Freeze

Deliverables:
- `BLUEPRINT.md`
- file tree contract
- API contract draft
- schema decisions

Acceptance:
- 구현자가 추가 질문 없이 scaffold를 만들 수 있다.

### Phase 2. Project Skeleton

Deliverables:
- Django project/app files
- settings
- urls
- celery
- requirements
- README
- AGENTS

Acceptance:
- `python manage.py check` passes.

### Phase 3. Domain Models

Deliverables:
- all models
- admin registration
- migrations

Acceptance:
- `python manage.py makemigrations`
- `python manage.py migrate`
- model tests pass.

### Phase 4. LLM Layer

Deliverables:
- base client
- Gemini client
- OpenAI client
- factory
- call logging
- JSON parser

Acceptance:
- provider switch works via `settings.USE_GEMINI`.
- missing key fails clearly.
- no fallback response exists.

### Phase 5. Population API

Deliverables:
- serializers/views for agendas and clusters
- cluster expansion service
- seed merge logic

Acceptance:
- agenda CRUD works.
- cluster expansion works with fake LLM.
- explicit weights are preserved.

### Phase 6. Memory Engine

Deliverables:
- memory service
- topic selection
- raw turn retrieval
- topic link/update logic

Acceptance:
- selected topic raw turns are fully loaded into prompt context.
- no session memory class is introduced.

### Phase 7. Prediction Engine

Deliverables:
- prediction service
- Celery task
- shock loop
- cluster state generation
- hybrid persona sampling heuristic

Acceptance:
- fake LLM can complete a full run.
- failed LLM JSON marks run failed.

### Phase 8. Aggregation

Deliverables:
- weighted opinion distribution
- risk/evidence aggregation
- result summary

Acceptance:
- normalized cluster weights produce deterministic distribution.

### Phase 9. API Tests and Docs

Deliverables:
- API tests
- memory tests
- prediction tests
- README curl examples

Acceptance:
- full test suite passes.
- README can guide a clean local run.

## 15. Open Questions For Later

- v1에서 PostgreSQL JSON indexing까지 미리 고려할지.
- LLM prompt 전문을 `LLMCallLog`에 저장할지, hash와 compact payload만 저장할지.
- stance taxonomy를 고정 enum으로 둘지 LLM-generated label로 둘지.
- shock event를 사용자가 전부 입력하게 할지, 추후 LLM 자동 생성 옵션을 둘지.
- long-run 비용 제어를 위해 run-level token budget을 둘지.
