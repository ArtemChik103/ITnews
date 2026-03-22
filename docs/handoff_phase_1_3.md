# Handoff: Phases 1-3

## Статус

- Фаза 1: закрыта baseline-реализацией. Локальный стек поднимается через Docker Compose, backend отвечает на `GET /health`, сервисные проверки по PostgreSQL, Neo4j, Redis и Qdrant проходят.
- Фаза 2: закрыта baseline-реализацией. Ingestion читает минимум 3 RSS-источника и опционально NewsAPI, чистит HTML, нормализует текст, определяет язык и сохраняет статьи в PostgreSQL с дедупликацией по `url`.
- Фаза 3: закрыта baseline-реализацией. Из статьи извлекаются `PERSON`, `ORGANIZATION`, `LOCATION`, после чего сущности и связи грузятся в Neo4j.

## PostgreSQL schema

Текущая схема создается автоматически при старте приложения.

Таблица `articles`:

- `id` integer primary key
- `title` varchar(512) not null
- `content_raw` text not null
- `content_clean` text not null
- `content_normalized` text not null
- `source` varchar(255) not null
- `url` varchar(1024) not null unique
- `published_at` timestamptz null
- `language` varchar(8) not null
- `ingested_at` timestamptz not null default now()

Индексы и ограничения:

- `uq_articles_url`
- `ix_articles_source_published_at`

## Sources and status

- `https://techcrunch.com/feed/` — active
- `https://www.wired.com/feed/rss` — active
- `https://feeds.arstechnica.com/arstechnica/index` — active
- `NewsAPI` — optional, controlled by `ENABLE_NEWS_API` and local `NEWS_API_KEY`

## NLP pipeline

1. Берется `title + content_clean`.
2. Rule-based entity extraction ищет title-cased последовательности и известные organization/location aliases.
3. Entity classification относит кандидата к `PERSON`, `ORGANIZATION`, `LOCATION`.
4. Relation extraction применяет baseline-patterns для `ASSOCIATED_WITH` и `LOCATED_IN`.
5. В Neo4j статья связывается с сущностями через `MENTIONS`, а relations пишутся как `RELATED_TO {type: ...}`.

## Neo4j schema

Узлы:

- `Article`
- `Entity`
- `Person`
- `Organization`
- `Location`

Связи:

- `(:Article)-[:MENTIONS]->(:Entity)`
- `(:Entity)-[:RELATED_TO {type: "ASSOCIATED_WITH"}]->(:Entity)`
- `(:Entity)-[:RELATED_TO {type: "LOCATED_IN"}]->(:Entity)`

Ограничения:

- unique `Article.article_id`
- unique composite key `Entity(normalized_name, entity_type)`

## Known limitations and technical debt

- Миграции отсутствуют, схема создается через `metadata.create_all()`.
- Scheduler встроен в процесс backend; для продовой эксплуатации его стоит вынести в отдельный worker/beat.
- Quality NER/RE пока rule-based и заметно ограничено на русском, аббревиатурах и неоднозначных именах.
- Эмбеддинги и запись в Qdrant пока не реализованы.
- Дедупликация статей сейчас идет по `url`; для более шумных источников позже потребуется нормализация canonical URL и контентные сигнатуры.
