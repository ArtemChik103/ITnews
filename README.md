# IT News Platform

Каркас платформы для сбора IT-новостей, очистки текста, извлечения сущностей и загрузки графа знаний.

## Реализовано

- Инфраструктура: FastAPI, PostgreSQL, Neo4j, Redis, Qdrant, Docker Compose, healthcheck.
- Ingestion: RSS для 3 источников, опциональный NewsAPI, очистка HTML, нормализация текста, language detection, дедупликация по URL.
- NLP/Graph: baseline rule-based NER и relation extraction, загрузка `Article` и `Entity`-графа в Neo4j.
- Embeddings/Vector: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, Qdrant collection `news_articles`, batch indexing и semantic search.
- Clustering: `HDBSCAN` с fallback на `KMeans`, cluster summary endpoint, синхронизация `cluster_id` между PostgreSQL и Qdrant.
- RAG: retrieval из Qdrant и Neo4j, Groq gateway с fallback по 3 моделям и retrieval-only degradation.

## Структура

```text
backend/
frontend/
docker/
docs/
```

## Быстрый старт

1. Скопировать `.env.example` в `.env`.
2. Изменить секреты при необходимости.
3. Выполнить `docker compose up --build`.
4. Открыть `http://localhost:8000/health`.

## API

- `GET /health`
- `POST /ingestion/run`
- `POST /indexing/run`
- `POST /clustering/run`
- `GET /articles`
- `POST /articles/{article_id}/graph`
- `GET /api/search/semantic`
- `GET /api/clusters`
- `POST /api/search`

## Модель Article

- `id`
- `title`
- `content_raw`
- `content_clean`
- `content_normalized`
- `source`
- `url`
- `published_at`
- `language`
- `embedding_status`
- `embedding_model`
- `embedded_at`
- `cluster_id`
- `clustered_at`
- `embedding_error`
- `ingested_at`

## Источники по умолчанию

- TechCrunch RSS
- Wired RSS
- Ars Technica RSS

## Схема графа

Узлы:

- `Article`
- `Entity`
- `Person`
- `Organization`
- `Location`

Связи:

- `(:Article)-[:MENTIONS]->(:Entity)`
- `(:Entity)-[:RELATED_TO {type: "..."}]->(:Entity)`

## Известные ограничения

- NER и relation extraction реализованы эвристиками и дают только baseline-качество.
- Планировщик встроен в backend через APScheduler; при росте нагрузки его стоит вынести в отдельный worker.
- Миграции схемы БД пока заменены startup-изменениями через `ALTER TABLE ... IF NOT EXISTS`.
- `sentence-transformers` и `torch` делают backend-образ заметно тяжелее.
- RAG ответ зависит от доступности Groq; при ошибках генерации endpoint уходит в retrieval-only режим.
