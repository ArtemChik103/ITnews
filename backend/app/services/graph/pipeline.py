from dataclasses import asdict

from app.models.article import Article
from app.services.graph.neo4j import Neo4jGraphService
from app.services.nlp.pipeline import extract_entities, extract_relations


async def graph_article(article: Article) -> dict:
    entities = extract_entities(article)
    relations = extract_relations(article, entities)
    graph = Neo4jGraphService()
    try:
        persisted = await graph.upsert_article_graph(article, entities, relations)
    finally:
        await graph.close()
    return {
        "article_id": article.id,
        "entities": [asdict(entity) for entity in entities],
        "relations": [asdict(relation) for relation in relations],
        "persisted": persisted,
    }
