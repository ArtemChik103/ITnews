from __future__ import annotations

import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.search import SearchResponse
from app.services.llm.groq_gateway import GroqGateway
from app.services.retrieval.service import RetrievalResult, RetrievalService

LLM_BUDGET_SECONDS = 8


class RagService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.retrieval_service = RetrievalService(session)
        self.llm_gateway = GroqGateway()

    async def answer(
        self,
        question: str,
        top_k: int,
        use_graph: bool,
        filters: dict | None = None,
    ) -> SearchResponse:
        retrieval = await self.retrieval_service.retrieve(question, top_k=top_k, filters=filters, use_graph=use_graph)
        if not retrieval.articles:
            return SearchResponse(
                answer="No relevant articles were found for this question.",
                sources=[],
                entities=[],
                graph_edges=[],
                retrieval_debug={
                    "vector_hits": 0,
                    "graph_hits": 0,
                    "llm_provider": None,
                    "llm_model": None,
                    "degraded_mode": None,
                },
                confidence=0.0,
                status="no_relevant_articles",
            )

        messages = build_rag_messages(question=question, retrieval=retrieval)
        try:
            llm_result = await asyncio.wait_for(
                self.llm_gateway.complete(messages=messages),
                timeout=LLM_BUDGET_SECONDS,
            )
            parsed = parse_llm_output(llm_result["text"])
            answer = parsed["answer"]
            confidence = parsed["confidence"]
            status = "success" if llm_result["degraded_mode"] is None else "degraded"
            degraded_mode = llm_result["degraded_mode"]
        except Exception:
            llm_result = {"provider": None, "model": None}
            answer = build_retrieval_only_answer(retrieval)
            confidence = 0.35
            status = "degraded"
            degraded_mode = "retrieval_only"

        return SearchResponse(
            answer=answer,
            sources=[
                {
                    "article_id": article.article_id,
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                }
                for article in retrieval.articles
            ],
            entities=[{"name": entity["name"], "type": entity["type"]} for entity in retrieval.entities],
            graph_edges=[
                {
                    "from": edge.from_name,
                    "relation": edge.relation,
                    "to": edge.to_name,
                    "source_article_ids": edge.source_article_ids,
                }
                for edge in retrieval.graph_edges
            ],
            retrieval_debug={
                "vector_hits": len(retrieval.articles),
                "graph_hits": len(retrieval.graph_edges),
                "llm_provider": llm_result["provider"],
                "llm_model": llm_result["model"],
                "degraded_mode": degraded_mode,
            },
            confidence=confidence,
            status=status,
        )


def build_rag_messages(question: str, retrieval: RetrievalResult) -> list[dict]:
    article_lines = []
    for article in retrieval.articles[:5]:
        article_lines.append(
            "\n".join(
                [
                    f"article_id: {article.article_id}",
                    f"title: {article.title}",
                    f"source: {article.source}",
                    f"published_at: {article.published_at.isoformat() if article.published_at else 'unknown'}",
                    f"url: {article.url}",
                    f"snippet: {article.snippet}",
                ]
            )
        )

    graph_lines = [
        f"{edge.from_name} | {edge.relation} | {edge.to_name} | source_article_ids={edge.source_article_ids}"
        for edge in retrieval.graph_edges[:20]
    ]

    system = (
        "You answer only from the supplied context. Do not invent facts. "
        "If context is insufficient, say so explicitly. Separate fact from interpretation. "
        "Return strict JSON with keys: answer, used_sources, mentioned_entities, confidence."
    )
    user = "\n\n".join(
        [
            f"Question: {question}",
            "News context:",
            "\n\n".join(article_lines),
            "Graph context:",
            "\n".join(graph_lines) or "none",
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_llm_output(text: str) -> dict:
    try:
        payload = json.loads(text)
        answer = payload.get("answer") or text
        if isinstance(answer, list):
            answer = "\n".join(str(item) for item in answer)
        return {
            "answer": str(answer),
            "confidence": float(payload.get("confidence", 0.6)),
        }
    except Exception:  # noqa: BLE001
        return {"answer": text.strip(), "confidence": 0.55}


def build_retrieval_only_answer(retrieval: RetrievalResult) -> str:
    lines = ["Generation was unavailable. Relevant retrieved articles:"]
    for article in retrieval.articles[:5]:
        lines.append(f"- {article.title} ({article.source})")
    if retrieval.graph_edges:
        lines.append("Graph signals:")
        for edge in retrieval.graph_edges[:5]:
            lines.append(f"- {edge.from_name} {edge.relation} {edge.to_name}")
    return "\n".join(lines)
