export interface ArticleRead {
  id: number;
  title: string;
  source: string;
  url: string;
  language: string;
  embedding_status: string;
  embedding_model: string | null;
  embedded_at: string | null;
  cluster_id: number | null;
  clustered_at: string | null;
  embedding_error: string | null;
  published_at: string | null;
  ingested_at: string;
}

export interface ArticleListResponse {
  items: ArticleRead[];
  page: number;
  page_size: number;
  total: number;
}

export interface ArticleDetail {
  id: number;
  title: string;
  content_clean: string;
  source: string;
  url: string;
  published_at: string | null;
  language: string;
  cluster_id: number | null;
  entities: { name: string; type?: string }[];
  related_articles: {
    id: number;
    title: string;
    source: string;
    url: string;
    published_at: string | null;
  }[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  from: string;
  relation: string;
  to: string;
  source_article_ids: number[];
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SearchSource {
  article_id: number;
  title: string;
  url: string;
  source: string;
}

export interface SearchEntity {
  name: string;
  type: string;
}

export interface RetrievalDebug {
  vector_hits: number;
  graph_hits: number;
  llm_provider: string | null;
  llm_model: string | null;
  degraded_mode: string | null;
}

export interface SearchResponse {
  answer: string;
  sources: SearchSource[];
  entities: SearchEntity[];
  graph_edges: GraphEdge[];
  retrieval_debug: RetrievalDebug;
  confidence: number;
  status: string;
}

export interface SearchRequest {
  question: string;
  top_k?: number;
  use_graph?: boolean;
  source_filter?: string[];
  date_from?: string;
  date_to?: string;
}

export interface ClusterSummaryItem {
  cluster_id: number;
  size: number;
  sample_articles: {
    article_id: number;
    title: string;
    source: string;
    url: string;
    published_at: string | null;
    cluster_id: number | null;
    score: number;
  }[];
  top_sources: string[];
}

export interface EntityDetail {
  name: string;
  type: string;
  articles: {
    article_id: number;
    title: string;
    source: string;
    url: string;
    published_at: string | null;
  }[];
  related_entities: SearchEntity[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SearchSource[];
  entities?: SearchEntity[];
  graphEdges?: GraphEdge[];
  status?: string;
  confidence?: number;
  retrievalDebug?: RetrievalDebug;
  timestamp: number;
}

export interface FilterState {
  source: string;
  language: string;
  clusterId: string;
  dateFrom: string;
  dateTo: string;
  entityType: string;
  page: number;
  pageSize: number;
  sort: 'published_at' | 'ingested_at';
}
