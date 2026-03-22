import asyncio

from neo4j import AsyncGraphDatabase

from app.core.config import get_settings
from app.models.article import Article
from app.services.nlp.pipeline import normalize_entity_name
from app.services.nlp.schemas import ExtractedEntity, ExtractedRelation


class Neo4jGraphService:
    _constraints_ready = False
    _constraint_lock = asyncio.Lock()

    def __init__(self) -> None:
        settings = get_settings()
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self) -> None:
        await self.driver.close()

    async def ensure_constraints(self) -> None:
        if self.__class__._constraints_ready:
            return

        async with self.__class__._constraint_lock:
            if self.__class__._constraints_ready:
                return

            async with self.driver.session() as session:
                result = await session.run(
                    "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE"
                )
                await result.consume()
                result = await session.run(
                    "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE (e.normalized_name, e.entity_type) IS UNIQUE"
                )
                await result.consume()

            self.__class__._constraints_ready = True

    @classmethod
    def mark_constraints_ready(cls) -> None:
        cls._constraints_ready = True

    async def initialize(self) -> None:
        await self.ensure_constraints()

    async def get_article_entities(self, article_id: int) -> list[str]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (:Article {article_id: $article_id})-[:MENTIONS]->(e:Entity)
                RETURN e.name AS name
                ORDER BY e.name
                """,
                article_id=article_id,
            )
            rows = await result.data()
        return [row["name"] for row in rows]

    async def get_context(self, article_ids: list[int], max_entities: int, max_relations: int) -> dict:
        async with self.driver.session() as session:
            entity_result = await session.run(
                """
                MATCH (a:Article)-[:MENTIONS]->(e:Entity)
                WHERE a.article_id IN $article_ids
                RETURN e.name AS name, e.entity_type AS type, count(DISTINCT a) AS mentions
                ORDER BY mentions DESC, name ASC
                LIMIT $max_entities
                """,
                article_ids=article_ids,
                max_entities=max_entities,
            )
            entities = await entity_result.data()

            relation_result = await session.run(
                """
                MATCH (a:Article)-[:MENTIONS]->(seed:Entity)
                WHERE a.article_id IN $article_ids
                WITH collect(DISTINCT seed.normalized_name) AS seed_names
                MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
                WHERE source.normalized_name IN seed_names OR target.normalized_name IN seed_names
                OPTIONAL MATCH (article:Article)-[:MENTIONS]->(source)
                WHERE article.article_id IN $article_ids
                RETURN source.name AS from_name,
                       r.type AS relation,
                       target.name AS to_name,
                       collect(DISTINCT article.article_id) AS source_article_ids,
                       size(collect(DISTINCT article.article_id)) AS source_count
                ORDER BY source_count DESC, from_name ASC
                LIMIT $max_relations
                """,
                article_ids=article_ids,
                max_relations=max_relations,
            )
            edges = await relation_result.data()

        return {
            "entities": [{"name": item["name"], "type": item["type"]} for item in entities],
            "edges": [
                {
                    "from": item["from_name"],
                    "relation": item["relation"],
                    "to": item["to_name"],
                    "source_article_ids": [article_id for article_id in item["source_article_ids"] if article_id is not None],
                }
                for item in edges
            ],
        }

    async def upsert_article_graph(
        self,
        article: Article,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
    ) -> dict:
        await self.ensure_constraints()

        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (article:Article {article_id: $article_id})
                SET article.title = $title,
                    article.url = $url,
                    article.source = $source,
                    article.language = $language,
                    article.published_at = $published_at
                """,
                article_id=article.id,
                title=article.title,
                url=article.url,
                source=article.source,
                language=article.language,
                published_at=article.published_at.isoformat() if article.published_at else None,
            )

            for entity in entities:
                labels = ":Entity"
                if entity.entity_type == "PERSON":
                    labels += ":Person"
                elif entity.entity_type == "ORGANIZATION":
                    labels += ":Organization"
                elif entity.entity_type == "LOCATION":
                    labels += ":Location"

                await session.run(
                    f"""
                    MERGE (e{labels} {{normalized_name: $normalized_name, entity_type: $entity_type}})
                    SET e.name = $name
                    WITH e
                    MATCH (article:Article {{article_id: $article_id}})
                    MERGE (article)-[:MENTIONS]->(e)
                    """,
                    normalized_name=entity.normalized_name,
                    entity_type=entity.entity_type,
                    name=entity.name,
                    article_id=article.id,
                )

            for relation in relations:
                await session.run(
                    """
                    MATCH (source:Entity {normalized_name: $source_normalized, entity_type: $source_type})
                    MATCH (target:Entity {normalized_name: $target_normalized, entity_type: $target_type})
                    MERGE (source)-[r:RELATED_TO {type: $relation_type}]->(target)
                    """,
                    source_normalized=normalize_entity_name(relation.source_name),
                    source_type=relation.source_type,
                    target_normalized=normalize_entity_name(relation.target_name),
                    target_type=relation.target_type,
                    relation_type=relation.relation_type,
                )

        return {"entities": len(entities), "relations": len(relations)}
