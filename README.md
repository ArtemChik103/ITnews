# IT News Platform

Каркас платформы для сбора IT-новостей, очистки текста, извлечения сущностей и загрузки графа знаний.

## Реализовано

- Инфраструктура: FastAPI, PostgreSQL, Neo4j, Redis, Qdrant, Docker Compose, healthcheck.
- Ingestion: RSS для 3 источников, опциональный NewsAPI, очистка HTML, нормализация текста, language detection, дедупликация по URL.
- NLP/Graph: baseline rule-based NER и relation extraction, загрузка `Article` и `Entity`-графа в Neo4j.

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
- `GET /articles`
- `POST /articles/{article_id}/graph`

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
- Эмбеддинги и загрузка в Qdrant пока не реализованы.
- Миграции схемы БД пока не добавлены.
