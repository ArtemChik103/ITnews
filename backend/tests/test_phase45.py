import numpy as np
import pytest

from app.services.clustering.service import cluster_vectors
from app.services.embeddings.service import build_embedding_input
from app.services.rag.service import RagService
from app.services.retrieval.service import RetrievalResult, RetrievedArticle, RetrievedGraphEdge


def test_build_embedding_input_truncates_and_uses_title() -> None:
    content = "a" * 5000
    result = build_embedding_input("Title", content)
    assert result.startswith("Title\n\n")
    assert len(result.split("\n\n", maxsplit=1)[1]) == 4000


def test_cluster_vectors_uses_kmeans_for_small_dataset() -> None:
    matrix = np.random.rand(10, 384).astype(np.float32)
    labels, algorithm = cluster_vectors(matrix, hdbscan_threshold=50, min_cluster_size=5)
    assert algorithm == "kmeans"
    assert len(labels) == 10


def test_cluster_vectors_uses_hdbscan_for_large_dataset() -> None:
    matrix = np.random.rand(60, 384).astype(np.float32)
    labels, algorithm = cluster_vectors(matrix, hdbscan_threshold=50, min_cluster_size=5)
    assert algorithm == "hdbscan"
    assert len(labels) == 60


@pytest.mark.asyncio
async def test_rag_returns_retrieval_only_when_llm_fails() -> None:
    service = RagService(session=None)  # type: ignore[arg-type]
    service.retrieval_service.retrieve = fake_retrieve  # type: ignore[method-assign]
    service.llm_gateway.complete = fake_complete_failure  # type: ignore[method-assign]

    response = await service.answer(question="What happened?", top_k=5, use_graph=True)

    assert response.status == "degraded"
    assert response.retrieval_debug.degraded_mode == "retrieval_only"
    assert response.sources


async def fake_retrieve(*args, **kwargs) -> RetrievalResult:  # noqa: ANN002, ANN003
    del args, kwargs
    return RetrievalResult(
        articles=[
            RetrievedArticle(
                article_id=1,
                title="Example article",
                source="example",
                url="https://example.com/article",
                published_at=None,
                cluster_id=1,
                score=0.9,
                snippet="Example snippet",
                entity_names=["Example Org"],
            )
        ],
        entities=[{"name": "Example Org", "type": "ORGANIZATION"}],
        graph_edges=[RetrievedGraphEdge(from_name="Alice", relation="ASSOCIATED_WITH", to_name="Example Org", source_article_ids=[1])],
        graph_available=True,
    )


async def fake_complete_failure(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003
    del args, kwargs
    raise RuntimeError("llm unavailable")
