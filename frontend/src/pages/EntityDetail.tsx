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
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { fetchEntityDetail, fetchGraph } from '../api/client';
import GraphView from '../components/GraphView';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function EntityDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const entityName = decodeURIComponent(name ?? '');

  const { data: entity, isLoading, error } = useQuery({
    queryKey: ['entity', entityName],
    queryFn: () => fetchEntityDetail(entityName),
    enabled: !!entityName,
  });

  const graphQuery = useQuery({
    queryKey: ['graph-entity', entityName],
    queryFn: () => fetchGraph({ entity_name: entityName }),
    enabled: !!entityName,
  });

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton width="40%" height={40} />
        <Skeleton width="100%" height={300} sx={{ mt: 2 }} />
      </Box>
    );
  }

  if (error || !entity) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Сущность «{entityName}» не найдена</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Назад
        </Button>
      </Box>
    );
  }

  const typeColors: Record<string, 'primary' | 'secondary' | 'success' | 'default'> = {
    PERSON: 'primary',
    ORGANIZATION: 'secondary',
    LOCATION: 'success',
  };

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Назад
      </Button>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography variant="h5">{entity.name}</Typography>
        <Chip label={entity.type} color={typeColors[entity.type] ?? 'default'} size="small" />
      </Box>

      {/* Graph */}
      {graphQuery.data && (graphQuery.data.nodes.length > 0 || graphQuery.data.edges.length > 0) && (
        <Box sx={{ height: 300, mb: 3, borderRadius: 2, overflow: 'hidden', border: 1, borderColor: 'divider' }}>
          <GraphView
            nodes={graphQuery.data.nodes}
            edges={graphQuery.data.edges}
            selectedNode={entityName.toLowerCase().replace(/\s+/g, '_')}
            onNodeClick={(_, label) => {
              if (label !== entity.name) navigate(`/entities/${encodeURIComponent(label)}`);
            }}
          />
        </Box>
      )}

      {/* Related entities */}
      {entity.related_entities.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            🔗 Связанные сущности
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {entity.related_entities.map((re) => (
              <Chip
                key={re.name}
                label={re.name}
                size="small"
                color={typeColors[re.type] ?? 'default'}
                component={RouterLink}
                to={`/entities/${encodeURIComponent(re.name)}`}
                clickable
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Articles */}
      <Typography variant="subtitle2" gutterBottom>
        📰 Статьи ({entity.articles.length})
      </Typography>
      {entity.articles.length === 0 ? (
        <Typography variant="body2" color="text.secondary">Нет связанных статей</Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {entity.articles.map((a) => (
            <Card key={a.article_id}>
              <CardActionArea onClick={() => navigate(`/articles/${a.article_id}`)}>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2">{a.title}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                    <Chip label={a.source} size="small" variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(a.published_at)}
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
