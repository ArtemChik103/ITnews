import { Box, Typography, Card, CardContent, CardActionArea, Chip, Skeleton } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import GraphView from '../components/GraphView';
import ArticleList from '../components/ArticleList';
import FilterPanel from '../components/FilterPanel';
import { fetchArticles, fetchClusters, fetchGraph } from '../api/client';
import { useFilterStore } from '../store/useFilterStore';
import { useGraphStore } from '../store/useGraphStore';

export default function Dashboard() {
  const navigate = useNavigate();
  const filters = useFilterStore();
  const searchGraphNodes = useGraphStore((s) => s.nodes);
  const searchGraphEdges = useGraphStore((s) => s.edges);

  const articlesQuery = useQuery({
    queryKey: ['articles', filters.page, filters.pageSize, filters.source, filters.language, filters.clusterId, filters.dateFrom, filters.dateTo, filters.sort],
    queryFn: () => fetchArticles(filters),
  });

  const clustersQuery = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
    staleTime: 60000,
  });

  const graphQuery = useQuery({
    queryKey: ['graph-default'],
    queryFn: () => fetchGraph({}),
    staleTime: 60000,
  });

  const displayNodes = searchGraphNodes.length > 0 ? searchGraphNodes : (graphQuery.data?.nodes ?? []);
  const displayEdges = searchGraphEdges.length > 0 ? searchGraphEdges : (graphQuery.data?.edges ?? []);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <FilterPanel />

      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden', flexDirection: { xs: 'column', lg: 'row' } }}>
        {/* Graph */}
        <Box sx={{ flex: { xs: 'none', lg: 1 }, height: { xs: 350, lg: 'auto' }, minHeight: 300, borderBottom: { xs: 1, lg: 0 }, borderRight: { lg: 1 }, borderColor: 'divider' }}>
          <GraphView
            nodes={displayNodes}
            edges={displayEdges}
            onNodeClick={(_, label) => navigate(`/entities/${encodeURIComponent(label)}`)}
          />
        </Box>

        {/* Right panel */}
        <Box sx={{ flex: { xs: 1, lg: 1 }, overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Clusters summary */}
          {clustersQuery.data && clustersQuery.data.length > 0 && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                📂 Кластеры
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {clustersQuery.isLoading && Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} width={120} height={32} variant="rounded" />
                ))}
                {clustersQuery.data.slice(0, 8).map((c) => (
                  <Card key={c.cluster_id} sx={{ minWidth: 0 }}>
                    <CardActionArea onClick={() => navigate(`/clusters/${c.cluster_id}`)}>
                      <CardContent sx={{ py: 1, px: 1.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip label={`#${c.cluster_id}`} size="small" color="secondary" />
                          <Typography variant="caption">{c.size} статей</Typography>
                        </Box>
                      </CardContent>
                    </CardActionArea>
                  </Card>
                ))}
              </Box>
            </Box>
          )}

          {/* Articles */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              📰 Последние статьи
            </Typography>
            <ArticleList
              articles={articlesQuery.data?.items ?? []}
              total={articlesQuery.data?.total ?? 0}
              page={filters.page}
              pageSize={filters.pageSize}
              onPageChange={filters.setPage}
              isLoading={articlesQuery.isLoading}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
