from neo4j import AsyncGraphDatabase

from app.core.config import get_settings
from app.models.article import Article
from app.services.nlp.pipeline import normalize_entity_name
from app.services.nlp.schemas import ExtractedEntity, ExtractedRelation


class Neo4jGraphService:
    def __init__(self) -> None:
        settings = get_settings()
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self) -> None:
        await self.driver.close()

    async def ensure_constraints(self) -> None:
        async with self.driver.session() as session:
            await session.run("CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE")
            await session.run(
                "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE (e.normalized_name, e.entity_type) IS UNIQUE"
            )

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
