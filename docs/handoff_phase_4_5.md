# Handoff: Phases 4-5

## Что добавлено

- `embedding_service` на `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `vector_store_service` на Qdrant collection `news_articles`
- `clustering_service` с `HDBSCAN` и fallback `KMeans`
- batch indexing job и reclustering job через APScheduler
- `GET /api/search/semantic`
- `GET /api/clusters`
- `llm_gateway` для Groq
- `retrieval_service`
- `rag_service`
- `POST /api/search`

## Изменения в данных

В `articles` добавлены поля:

- `embedding_status`
- `embedding_model`
- `embedded_at`
- `cluster_id`
- `clustered_at`
- `embedding_error`
- `embedding_attempts`

Startup logic выполняет `ALTER TABLE ... IF NOT EXISTS`, чтобы обновить уже существующую PostgreSQL схему без отдельной миграции.

## Retrieval and vector flow

1. После ingestion статья получает `embedding_status = pending`.
2. Job `/indexing/run` выбирает `pending/failed` статьи с retry limit.
3. Формируется текст вида `title + content_clean[:4000]`.
4. Генерируется L2-normalized embedding.
5. Вектор и payload пишутся в Qdrant.
6. В PostgreSQL обновляются `embedding_status`, `embedding_model`, `embedded_at`.
7. Reclustering пишет `cluster_id` обратно в PostgreSQL и Qdrant payload.

## Clustering rules

- `< 50` векторов: `KMeans`
- `>= 50` векторов: `HDBSCAN`
- noise points HDBSCAN сохраняются как `cluster_id = -1`

## RAG flow

1. `POST /api/search` строит query embedding той же моделью.
2. Retrieval идет в Qdrant.
3. По top articles запрашиваются entities/relations из Neo4j.
4. Контекст собирается из snippets и graph edges.
5. Groq вызывается по очереди:
   - `openai/gpt-oss-120b`
   - `llama-3.3-70b-versatile`
   - `llama-3.1-8b-instant`
6. Если все модели недоступны, API возвращает retrieval-only ответ.

## Env additions

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `EMBEDDING_MAX_CHARS`
- `EMBEDDING_MAX_RETRIES`
- `EMBEDDING_INDEX_INTERVAL_MINUTES`
- `CLUSTERING_INTERVAL_MINUTES`
- `CLUSTERING_HDBSCAN_THRESHOLD`
- `CLUSTERING_MIN_CLUSTER_SIZE`
- `LLM_PROVIDER`
- `GROQ_API_KEY`
- `GROQ_MODEL_PRIMARY`
- `GROQ_MODEL_FALLBACK`
- `GROQ_MODEL_FAST`
- `GROQ_API_URL`
- `GROQ_TIMEOUT_SECONDS`
- `RAG_TOP_K`
- `GRAPH_MAX_ENTITIES`
- `GRAPH_MAX_RELATIONS`
- `RAG_MAX_ARTICLE_SNIPPET_CHARS`
- `RAG_CONTEXT_TOKEN_BUDGET`

## Проверки

Локально подтверждено:

- Python import приложения проходит
- `pytest` проходит: 8 tests passed
- покрыты ветки embedding input, clustering selection, degraded RAG

Отдельно:

- контейнерная интеграционная проверка фаз 4-5 была заблокирована локальным сбоем Docker Desktop engine (`500 Internal Server Error` на Docker API) во время пересборки тяжелого backend image с `torch`.

## Известные ограничения

- Embedding model скачивается при первом запуске, что увеличивает время cold start.
- RAG output пока парсится best-effort из JSON/text, без строгого structured output enforcement.
- Freshness boost реализован простым score offset.
- Для multi-source filter в RAG используется OR-фильтр в Qdrant без отдельного reranker.
