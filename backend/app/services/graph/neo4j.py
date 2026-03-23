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

    async def get_default_graph(self, max_nodes: int = 30, max_edges: int = 50) -> dict:
        async with self.driver.session() as session:
            edge_result = await session.run(
                """
                MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
                WHERE size(coalesce(r.article_ids, [])) > 0
                RETURN source.name AS from_name, source.entity_type AS from_type,
                       r.type AS relation,
                       target.name AS to_name, target.entity_type AS to_type,
                       coalesce(r.article_ids, []) AS source_article_ids,
                       size(coalesce(r.article_ids, [])) AS weight
                ORDER BY weight DESC
                LIMIT $max_edges
                """,
                max_edges=max_edges,
            )
            edges_raw = await edge_result.data()

            nodes_map: dict[str, dict] = {}
            for e in edges_raw:
                for name, etype in [(e["from_name"], e["from_type"]), (e["to_name"], e["to_type"])]:
                    nid = name.lower().replace(" ", "_")
                    if nid not in nodes_map:
                        nodes_map[nid] = {"name": name, "type": etype or "Entity", "id": nid}

            return {
                "nodes": list(nodes_map.values())[:max_nodes],
                "edges": [
                    {
                        "from_name": e["from_name"],
                        "relation": e["relation"],
                        "to_name": e["to_name"],
                        "source_article_ids": [a for a in e["source_article_ids"] if a is not None],
                    }
                    for e in edges_raw
                ],
            }

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
                WHERE (source.normalized_name IN seed_names OR target.normalized_name IN seed_names)
                  AND size(coalesce(r.article_ids, [])) > 0
                RETURN source.name AS from_name,
                       r.type AS relation,
                       target.name AS to_name,
                       coalesce(r.article_ids, []) AS source_article_ids,
                       size(coalesce(r.article_ids, [])) AS source_count
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
            await session.run(
                """
                MATCH (:Article {article_id: $article_id})-[m:MENTIONS]->(:Entity)
                DELETE m
                """,
                article_id=article.id,
            )
            await session.run(
                """
                MATCH (:Entity)-[r:RELATED_TO]->(:Entity)
                WHERE $article_id IN coalesce(r.article_ids, [])
                SET r.article_ids = [existing_id IN coalesce(r.article_ids, []) WHERE existing_id <> $article_id]
                WITH r
                WHERE size(coalesce(r.article_ids, [])) = 0
                DELETE r
                """,
                article_id=article.id,
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
                    ON CREATE SET r.article_ids = [$article_id]
                    ON MATCH SET r.article_ids =
                        CASE
                            WHEN $article_id IN coalesce(r.article_ids, []) THEN r.article_ids
                            ELSE coalesce(r.article_ids, []) + $article_id
                        END
                    """,
                    source_normalized=normalize_entity_name(relation.source_name),
                    source_type=relation.source_type,
                    target_normalized=normalize_entity_name(relation.target_name),
                    target_type=relation.target_type,
                    relation_type=relation.relation_type,
                    article_id=article.id,
                )

        return {"entities": len(entities), "relations": len(relations)}

    async def get_entity_detail(self, entity_name: str) -> dict | None:
        async with self.driver.session() as session:
            entity_result = await session.run(
                """
                MATCH (e:Entity)
                WHERE toLower(e.name) = toLower($name) OR toLower(e.normalized_name) = toLower($name)
                RETURN e.name AS name, e.entity_type AS type
                LIMIT 1
                """,
                name=entity_name,
            )
            entity_data = await entity_result.data()
            if not entity_data:
                return None
            entity = entity_data[0]

            articles_result = await session.run(
                """
                MATCH (a:Article)-[:MENTIONS]->(e:Entity)
                WHERE toLower(e.name) = toLower($name) OR toLower(e.normalized_name) = toLower($name)
                RETURN a.article_id AS article_id, a.title AS title, a.source AS source,
                       a.url AS url, a.published_at AS published_at
                ORDER BY a.published_at DESC
                LIMIT 50
                """,
                name=entity_name,
            )
            articles = await articles_result.data()

            related_result = await session.run(
                """
                MATCH (e:Entity)-[:RELATED_TO]-(other:Entity)
                WHERE (toLower(e.name) = toLower($name) OR toLower(e.normalized_name) = toLower($name))
                  AND e <> other
                RETURN DISTINCT other.name AS name, other.entity_type AS type
                ORDER BY name
                LIMIT 30
                """,
                name=entity_name,
            )
            related = await related_result.data()

        return {
            "name": entity["name"],
            "type": entity["type"],
            "articles": articles,
            "related_entities": [{"name": r["name"], "type": r["type"]} for r in related],
        }

    async def get_graph_for_entity(self, entity_name: str, max_nodes: int = 50, max_edges: int = 80) -> dict:
        async with self.driver.session() as session:
            nodes_result = await session.run(
                """
                MATCH (center:Entity)
                WHERE toLower(center.name) = toLower($name) OR toLower(center.normalized_name) = toLower($name)
                OPTIONAL MATCH (center)-[:RELATED_TO]-(neighbor:Entity)
                WITH collect(DISTINCT center) + collect(DISTINCT neighbor) AS all_entities
                UNWIND all_entities AS e
                WITH DISTINCT e
                LIMIT $max_nodes
                RETURN e.name AS name, e.entity_type AS type, e.normalized_name AS id
                """,
                name=entity_name,
                max_nodes=max_nodes,
            )
            nodes = await nodes_result.data()

            node_ids = [n["id"] for n in nodes]

            edges_result = await session.run(
                """
                MATCH (s:Entity)-[r:RELATED_TO]->(t:Entity)
                WHERE s.normalized_name IN $node_ids AND t.normalized_name IN $node_ids
                RETURN s.name AS from_name, r.type AS relation, t.name AS to_name,
                       coalesce(r.article_ids, []) AS source_article_ids
                LIMIT $max_edges
                """,
                node_ids=node_ids,
                max_edges=max_edges,
            )
            edges = await edges_result.data()

        return {"nodes": nodes, "edges": edges}

    async def get_graph_for_article(self, article_id: int, max_nodes: int = 50, max_edges: int = 80) -> dict:
        async with self.driver.session() as session:
            nodes_result = await session.run(
                """
                MATCH (a:Article {article_id: $article_id})-[:MENTIONS]->(e:Entity)
                RETURN DISTINCT e.name AS name, e.entity_type AS type, e.normalized_name AS id
                LIMIT $max_nodes
                """,
                article_id=article_id,
                max_nodes=max_nodes,
            )
            nodes = await nodes_result.data()

            node_ids = [n["id"] for n in nodes]

            edges_result = await session.run(
                """
                MATCH (s:Entity)-[r:RELATED_TO]->(t:Entity)
                WHERE s.normalized_name IN $node_ids AND t.normalized_name IN $node_ids
                RETURN s.name AS from_name, r.type AS relation, t.name AS to_name,
                       coalesce(r.article_ids, []) AS source_article_ids
                LIMIT $max_edges
                """,
                node_ids=node_ids,
                max_edges=max_edges,
            )
            edges = await edges_result.data()

        return {"nodes": nodes, "edges": edges}
