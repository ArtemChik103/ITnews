import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
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
  Divider,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { fetchArticleDetail } from '../api/client';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const articleId = Number(id);

  const { data: article, isLoading, error } = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => fetchArticleDetail(articleId),
    enabled: !isNaN(articleId),
  });

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton width="60%" height={40} />
        <Skeleton width="30%" height={24} sx={{ mt: 1 }} />
        <Skeleton width="100%" height={200} sx={{ mt: 2 }} />
      </Box>
    );
  }

  if (error || !article) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Статья не найдена</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Назад
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 900, mx: 'auto' }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Назад
      </Button>

      <Typography variant="h5" gutterBottom>
        {article.title}
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 2 }}>
        <Chip label={article.source} color="primary" size="small" />
        <Typography variant="body2" color="text.secondary">
          {formatDate(article.published_at)}
        </Typography>
        <Chip label={article.language.toUpperCase()} size="small" variant="outlined" />
        {article.cluster_id != null && (
          <Chip
            label={`Кластер ${article.cluster_id}`}
            size="small"
            color="secondary"
            component={RouterLink}
            to={`/clusters/${article.cluster_id}`}
            clickable
          />
        )}
        <Button
          size="small"
          endIcon={<OpenInNewIcon />}
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Оригинал
        </Button>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Entities */}
      {article.entities.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            🏷️ Сущности
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {article.entities.map((e) => (
              <Chip
                key={e.name}
                label={e.name}
                size="small"
                component={RouterLink}
                to={`/entities/${encodeURIComponent(e.name)}`}
                clickable
                color={
                  e.type === 'PERSON' ? 'primary' :
                  e.type === 'ORGANIZATION' ? 'secondary' : 'default'
                }
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Content */}
      <Typography
        variant="body1"
        sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, mb: 3 }}
      >
        {article.content_clean}
      </Typography>

      {/* Related articles */}
      {article.related_articles.length > 0 && (
        <Box>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            📎 Похожие статьи
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {article.related_articles.map((ra) => (
              <Card key={ra.id}>
                <CardActionArea onClick={() => navigate(`/articles/${ra.id}`)}>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2">{ra.title}</Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                      <Chip label={ra.source} size="small" variant="outlined" />
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(ra.published_at)}
                      </Typography>
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}
