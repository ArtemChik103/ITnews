from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import delete, func, select
from sqlalchemy.orm import aliased

from app.db.session import SessionLocal
from app.models.article import Article, ArticleMention, Entity, EntityRelation
from app.services.nlp.pipeline import normalize_entity_name

if TYPE_CHECKING:
    from app.services.nlp.schemas import ExtractedEntity, ExtractedRelation


class Neo4jGraphService:
    """SQL-backed graph service replacing Neo4j with PostgreSQL tables."""

    async def close(self) -> None:
        pass

    async def initialize(self) -> None:
        pass

    async def get_article_entities(self, article_id: int) -> list[str]:
        async with SessionLocal() as session:
            stmt = (
                select(Entity.name)
                .join(ArticleMention, ArticleMention.entity_id == Entity.id)
                .where(ArticleMention.article_id == article_id)
                .order_by(Entity.name)
            )
            res = await session.scalars(stmt)
            return list(res.all())

    async def get_default_graph(self, max_nodes: int = 30, max_edges: int = 50) -> dict:
        async with SessionLocal() as session:
            E1 = aliased(Entity)
            E2 = aliased(Entity)

            stmt = (
                select(
                    E1.name.label("from_name"),
                    E1.entity_type.label("from_type"),
                    EntityRelation.relation_type.label("relation"),
                    E2.name.label("to_name"),
                    E2.entity_type.label("to_type"),
                    func.array_agg(EntityRelation.article_id).label("source_article_ids"),
                    func.count(EntityRelation.id).label("weight"),
                )
                .join(E1, EntityRelation.source_entity_id == E1.id)
                .join(E2, EntityRelation.target_entity_id == E2.id)
                .group_by(E1.name, E1.entity_type, EntityRelation.relation_type, E2.name, E2.entity_type)
                .order_by(func.count(EntityRelation.id).desc())
                .limit(max_edges)
            )

            res = await session.execute(stmt)
            edges_raw = res.all()

            nodes_map: dict[str, dict] = {}
            edges = []
            for row in edges_raw:
                for name, etype in [(row.from_name, row.from_type), (row.to_name, row.to_type)]:
                    nid = name.lower().replace(" ", "_")
                    if nid not in nodes_map:
                        nodes_map[nid] = {"name": name, "type": etype or "Entity", "id": nid}

                edges.append({
                    "from_name": row.from_name,
                    "relation": row.relation,
                    "to_name": row.to_name,
                    "source_article_ids": list(set(row.source_article_ids or [])),
                })

            return {
                "nodes": list(nodes_map.values())[:max_nodes],
                "edges": edges,
            }

    async def get_context(self, article_ids: list[int], max_entities: int, max_relations: int) -> dict:
        if not article_ids:
            return {"entities": [], "edges": []}

        async with SessionLocal() as session:
            top_entities_stmt = (
                select(Entity.name, Entity.entity_type, func.count(func.distinct(ArticleMention.article_id)).label("mentions"))
                .join(ArticleMention, ArticleMention.entity_id == Entity.id)
                .where(ArticleMention.article_id.in_(article_ids))
                .group_by(Entity.name, Entity.entity_type)
                .order_by(func.count(func.distinct(ArticleMention.article_id)).desc(), Entity.name.asc())
                .limit(max_entities)
            )
            ent_res = await session.execute(top_entities_stmt)
            entities = [{"name": row.name, "type": row.entity_type} for row in ent_res.all()]

            E1 = aliased(Entity)
            E2 = aliased(Entity)
            rel_stmt = (
                select(
                    E1.name.label("from_name"),
                    EntityRelation.relation_type.label("relation"),
                    E2.name.label("to_name"),
                    func.array_agg(EntityRelation.article_id).label("source_article_ids"),
                )
                .join(E1, EntityRelation.source_entity_id == E1.id)
                .join(E2, EntityRelation.target_entity_id == E2.id)
                .where(EntityRelation.article_id.in_(article_ids))
                .group_by(E1.name, EntityRelation.relation_type, E2.name)
                .limit(max_relations)
            )
            rel_res = await session.execute(rel_stmt)
            edges = [
                {
                    "from": row.from_name,
                    "relation": row.relation,
                    "to": row.to_name,
                    "source_article_ids": list(set(row.source_article_ids or [])),
                }
                for row in rel_res.all()
            ]

            return {"entities": entities, "edges": edges}

    async def upsert_article_graph(
        self,
        article: Article,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
    ) -> dict:
        async with SessionLocal() as session:
            # Delete old graph records for this article
            await session.execute(delete(ArticleMention).where(ArticleMention.article_id == article.id))
            await session.execute(delete(EntityRelation).where(EntityRelation.article_id == article.id))

            entity_map: dict[tuple[str, str], int] = {}

            for entity in entities:
                norm_name = entity.normalized_name
                etype = entity.entity_type
                key = (norm_name, etype)

                stmt = select(Entity).where(Entity.normalized_name == norm_name, Entity.entity_type == etype)
                existing = (await session.scalars(stmt)).first()
                if not existing:
                    existing = Entity(name=entity.name, normalized_name=norm_name, entity_type=etype)
                    session.add(existing)
                    await session.flush()

                entity_map[key] = existing.id

                # Link article mention
                mention_check = select(ArticleMention).where(
                    ArticleMention.article_id == article.id,
                    ArticleMention.entity_id == existing.id,
                )
                if not (await session.scalars(mention_check)).first():
                    session.add(ArticleMention(article_id=article.id, entity_id=existing.id))

            for rel in relations:
                src_norm = normalize_entity_name(rel.source_name)
                tgt_norm = normalize_entity_name(rel.target_name)

                src_id = entity_map.get((src_norm, rel.source_type))
                tgt_id = entity_map.get((tgt_norm, rel.target_type))

                if not src_id:
                    src_ent = (await session.scalars(select(Entity).where(Entity.normalized_name == src_norm, Entity.entity_type == rel.source_type))).first()
                    if not src_ent:
                        src_ent = Entity(name=rel.source_name, normalized_name=src_norm, entity_type=rel.source_type)
                        session.add(src_ent)
                        await session.flush()
                    src_id = src_ent.id

                if not tgt_id:
                    tgt_ent = (await session.scalars(select(Entity).where(Entity.normalized_name == tgt_norm, Entity.entity_type == rel.target_type))).first()
                    if not tgt_ent:
                        tgt_ent = Entity(name=rel.target_name, normalized_name=tgt_norm, entity_type=rel.target_type)
                        session.add(tgt_ent)
                        await session.flush()
                    tgt_id = tgt_ent.id

                session.add(EntityRelation(
                    source_entity_id=src_id,
                    target_entity_id=tgt_id,
                    relation_type=rel.relation_type,
                    article_id=article.id,
                ))

            await session.commit()
            return {"entities": len(entities), "relations": len(relations)}

    async def get_entity_detail(self, entity_name: str) -> dict | None:
        async with SessionLocal() as session:
            norm_name = normalize_entity_name(entity_name)
            stmt = select(Entity).where(
                (func.lower(Entity.name) == entity_name.lower()) | (Entity.normalized_name == norm_name)
            )
            entity = (await session.scalars(stmt)).first()
            if not entity:
                return None

            articles_stmt = (
                select(Article)
                .join(ArticleMention, ArticleMention.article_id == Article.id)
                .where(ArticleMention.entity_id == entity.id)
                .order_by(Article.published_at.desc())
                .limit(50)
            )
            articles = (await session.scalars(articles_stmt)).all()

            E1 = aliased(Entity)
            E2 = aliased(Entity)
            rel_stmt = (
                select(E2.name, E2.entity_type)
                .join(EntityRelation, EntityRelation.target_entity_id == E2.id)
                .where(EntityRelation.source_entity_id == entity.id)
                .union(
                    select(E1.name, E1.entity_type)
                    .join(EntityRelation, EntityRelation.source_entity_id == E1.id)
                    .where(EntityRelation.target_entity_id == entity.id)
                )
                .limit(30)
            )
            rel_res = await session.execute(rel_stmt)
            related = [{"name": row[0], "type": row[1]} for row in rel_res.all()]

            return {
                "name": entity.name,
                "type": entity.entity_type,
                "articles": [
                    {
                        "article_id": a.id,
                        "title": a.title,
                        "source": a.source,
                        "url": a.url,
                        "published_at": a.published_at.isoformat() if a.published_at else None,
                    }
                    for a in articles
                ],
                "related_entities": related,
            }

    async def get_graph_for_entity(self, entity_name: str, max_nodes: int = 50, max_edges: int = 80) -> dict:
        detail = await self.get_entity_detail(entity_name)
        if not detail:
            return {"nodes": [], "edges": []}
        return await self.get_default_graph(max_nodes=max_nodes, max_edges=max_edges)

    async def get_graph_for_article(self, article_id: int, max_nodes: int = 50, max_edges: int = 80) -> dict:
        async with SessionLocal() as session:
            nodes_stmt = (
                select(Entity.name, Entity.entity_type)
                .join(ArticleMention, ArticleMention.entity_id == Entity.id)
                .where(ArticleMention.article_id == article_id)
                .limit(max_nodes)
            )
            n_res = await session.execute(nodes_stmt)
            nodes = [
                {"name": row.name, "type": row.entity_type, "id": row.name.lower().replace(" ", "_")}
                for row in n_res.all()
            ]

            E1 = aliased(Entity)
            E2 = aliased(Entity)
            edges_stmt = (
                select(E1.name.label("from_name"), EntityRelation.relation_type.label("relation"), E2.name.label("to_name"))
                .join(E1, EntityRelation.source_entity_id == E1.id)
                .join(E2, EntityRelation.target_entity_id == E2.id)
                .where(EntityRelation.article_id == article_id)
                .limit(max_edges)
            )
            e_res = await session.execute(edges_stmt)
            edges = [
                {"from_name": row.from_name, "relation": row.relation, "to_name": row.to_name, "source_article_ids": [article_id]}
                for row in e_res.all()
            ]

            return {"nodes": nodes, "edges": edges}
