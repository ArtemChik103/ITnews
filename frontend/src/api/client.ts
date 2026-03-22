import axios from 'axios';
import type {
  ArticleDetail,
  ArticleListResponse,
  ClusterSummaryItem,
  EntityDetail,
  FilterState,
  GraphResponse,
  SearchRequest,
  SearchResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
});

export async function fetchArticles(filters: Partial<FilterState>): Promise<ArticleListResponse> {
  const params: Record<string, string | number> = {};
  if (filters.page) params.page = filters.page;
  if (filters.pageSize) params.page_size = filters.pageSize;
  if (filters.source) params.source = filters.source;
  if (filters.language) params.language = filters.language;
  if (filters.clusterId) params.cluster_id = filters.clusterId;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.sort) params.sort = filters.sort;
  const { data } = await api.get<ArticleListResponse>('/api/articles', { params });
  return data;
}

export async function fetchArticleDetail(id: number): Promise<ArticleDetail> {
  const { data } = await api.get<ArticleDetail>(`/api/articles/${id}`);
  return data;
}

export async function fetchGraph(params: {
  article_id?: number;
  entity_name?: string;
  query?: string;
}): Promise<GraphResponse> {
  const { data } = await api.get<GraphResponse>('/api/graph', { params });
  return data;
}

export async function fetchEntityDetail(name: string): Promise<EntityDetail> {
  const { data } = await api.get<EntityDetail>(`/api/entities/${encodeURIComponent(name)}`);
  return data;
}

export async function fetchClusters(): Promise<ClusterSummaryItem[]> {
  const { data } = await api.get<{ clusters: ClusterSummaryItem[] }>('/api/clusters');
  return data.clusters;
}

export async function searchRAG(request: SearchRequest): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>('/api/search', request);
  return data;
}

export async function semanticSearch(
  q: string,
  topK = 5,
  filters?: Partial<FilterState>,
): Promise<{ items: ArticleListResponse['items']; query: string; top_k: number }> {
  const params: Record<string, string | number> = { q, top_k: topK };
  if (filters?.source) params.source = filters.source;
  if (filters?.language) params.language = filters.language;
  if (filters?.dateFrom) params.date_from = filters.dateFrom;
  if (filters?.dateTo) params.date_to = filters.dateTo;
  const { data } = await api.get('/api/search/semantic', { params });
  return data;
}
