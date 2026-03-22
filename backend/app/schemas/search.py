from datetime import date, datetime

from pydantic import BaseModel, Field


class SemanticSearchItem(BaseModel):
    article_id: int
    title: str
    source: str
    url: str
    published_at: datetime | None
    cluster_id: int | None
    score: float


class SemanticSearchResponse(BaseModel):
    items: list[SemanticSearchItem]
    query: str
    top_k: int


class ClusterSummaryItem(BaseModel):
    cluster_id: int
    size: int
    sample_articles: list[SemanticSearchItem]
    top_sources: list[str]


class ClusterSummaryResponse(BaseModel):
    clusters: list[ClusterSummaryItem]


class SearchRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    use_graph: bool = True
    source_filter: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


class SearchSource(BaseModel):
    article_id: int
    title: str
    url: str
    source: str


class SearchEntity(BaseModel):
    name: str
    type: str


class GraphEdge(BaseModel):
    from_: str = Field(alias="from")
    relation: str
    to: str
    source_article_ids: list[int] = []

    model_config = {"populate_by_name": True}


class RetrievalDebug(BaseModel):
    vector_hits: int
    graph_hits: int
    llm_provider: str | None
    llm_model: str | None
    degraded_mode: str | None


class SearchResponse(BaseModel):
    answer: str
    sources: list[SearchSource]
    entities: list[SearchEntity]
    graph_edges: list[GraphEdge]
    retrieval_debug: RetrievalDebug
    confidence: float
    status: str


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    metadata: dict = {}


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EntityArticle(BaseModel):
    article_id: int
    title: str
    source: str
    url: str
    published_at: datetime | None


class EntityDetailResponse(BaseModel):
    name: str
    type: str
    articles: list[EntityArticle]
    related_entities: list[SearchEntity]
