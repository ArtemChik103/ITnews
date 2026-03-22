import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Chip,
  Card,
  CardContent,
  CardActionArea,
  Skeleton,
  Button,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { fetchClusters, fetchArticles } from '../api/client';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function ClusterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const clusterId = Number(id);

  const clustersQuery = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
    staleTime: 60000,
  });

  const articlesQuery = useQuery({
    queryKey: ['cluster-articles', clusterId],
    queryFn: () => fetchArticles({ clusterId: String(clusterId), pageSize: 50 }),
    enabled: !isNaN(clusterId),
  });

  const cluster = clustersQuery.data?.find((c) => c.cluster_id === clusterId);

  if (clustersQuery.isLoading || articlesQuery.isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton width="40%" height={40} />
        <Skeleton width="100%" height={200} sx={{ mt: 2 }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Назад
      </Button>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography variant="h5">Кластер #{clusterId}</Typography>
        {cluster && (
          <Chip label={`${cluster.size} статей`} color="secondary" size="small" />
        )}
      </Box>

      {cluster?.top_sources && cluster.top_sources.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Основные источники:</Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {cluster.top_sources.map((s) => (
              <Chip key={s} label={s} size="small" variant="outlined" />
            ))}
          </Box>
        </Box>
      )}

      {/* Articles in cluster */}
      <Typography variant="subtitle2" gutterBottom>
        📰 Статьи в кластере
      </Typography>

      {articlesQuery.data?.items.length === 0 ? (
        <Alert severity="info">В этом кластере нет статей</Alert>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {articlesQuery.data?.items.map((article) => (
            <Card key={article.id}>
              <CardActionArea onClick={() => navigate(`/articles/${article.id}`)}>
                <CardContent sx={{ py: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                    {article.title}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Chip label={article.source} size="small" variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(article.published_at)}
                    </Typography>
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
}
