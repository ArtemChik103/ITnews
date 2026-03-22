import {
  Box,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Chip,
  Skeleton,
  Pagination,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import type { ArticleRead } from '../types';

interface Props {
  articles: ArticleRead[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function ArticleSkeleton() {
  return (
    <Card>
      <CardContent>
        <Skeleton width="80%" height={24} />
        <Skeleton width="40%" height={18} sx={{ mt: 1 }} />
        <Skeleton width="60%" height={18} sx={{ mt: 0.5 }} />
      </CardContent>
    </Card>
  );
}

export default function ArticleList({ articles, total, page, pageSize, onPageChange, isLoading }: Props) {
  const navigate = useNavigate();
  const totalPages = Math.ceil(total / pageSize);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <ArticleSkeleton key={i} />
        ))}
      </Box>
    );
  }

  if (articles.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
        <Typography variant="body1">Статьи не найдены</Typography>
        <Typography variant="body2">Попробуйте изменить фильтры</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Typography variant="body2" color="text.secondary">
        Найдено: {total} статей
      </Typography>

      {articles.map((article) => (
        <Card key={article.id}>
          <CardActionArea
            onClick={() => navigate(`/articles/${article.id}`)}
            aria-label={`Открыть статью: ${article.title}`}
          >
            <CardContent sx={{ py: 1.5 }}>
              <Typography variant="subtitle2" sx={{ mb: 0.5, lineHeight: 1.3 }}>
                {article.title}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                <Chip label={article.source} size="small" variant="outlined" />
                <Typography variant="caption" color="text.secondary">
                  {formatDate(article.published_at)}
                </Typography>
                {article.cluster_id != null && (
                  <Chip
                    label={`Кластер ${article.cluster_id}`}
                    size="small"
                    color="secondary"
                    variant="outlined"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/clusters/${article.cluster_id}`);
                    }}
                    component="button"
                  />
                )}
                <Chip
                  label={article.language.toUpperCase()}
                  size="small"
                  sx={{ fontSize: '10px', height: 20 }}
                />
              </Box>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}

      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, p) => onPageChange(p)}
            color="primary"
            size="small"
          />
        </Box>
      )}
    </Box>
  );
}
