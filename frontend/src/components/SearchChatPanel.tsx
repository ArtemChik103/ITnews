import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Paper,
  Chip,
  Skeleton,
  Alert,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import type { ChatMessage, SearchResponse } from '../types';
import { searchRAG } from '../api/client';

interface Props {
  onGraphUpdate?: (edges: SearchResponse['graph_edges'], entities: SearchResponse['entities']) => void;
  onSourceClick?: (articleId: number) => void;
}

export default function SearchChatPanel({ onGraphUpdate, onSourceClick }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const handleSubmit = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await searchRAG({ question, top_k: 5, use_graph: true });
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
        entities: res.entities,
        graphEdges: res.graph_edges,
        status: res.status,
        confidence: res.confidence,
        retrievalDebug: res.retrieval_debug,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      onGraphUpdate?.(res.graph_edges, res.entities);
    } catch {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Ошибка при получении ответа. Попробуйте ещё раз.',
        status: 'error',
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const getStatusColor = (status?: string) => {
    if (status === 'success') return 'success';
    if (status === 'degraded') return 'warning';
    if (status === 'error' || status === 'retrieval_unavailable') return 'error';
    return 'info';
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Typography variant="h6" sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
        💬 RAG Поиск
      </Typography>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {messages.length === 0 && (
          <Box sx={{ textAlign: 'center', mt: 4, color: 'text.secondary' }}>
            <Typography variant="body1" gutterBottom>
              Задайте вопрос о новостях
            </Typography>
            <Typography variant="body2">
              Например: «Какие компании связаны с ИИ?»
            </Typography>
          </Box>
        )}

        {messages.map((msg) => (
          <Paper
            key={msg.id}
            elevation={0}
            sx={{
              p: 2,
              maxWidth: '90%',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
              color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
              borderRadius: 2,
            }}
          >
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {msg.content}
            </Typography>

            {msg.status && msg.status !== 'success' && msg.status !== 'error' && (
              <Alert severity={getStatusColor(msg.status) as 'warning' | 'info'} sx={{ mt: 1, py: 0 }}>
                {msg.status === 'degraded' && 'Ответ получен в режиме деградации'}
                {msg.status === 'no_relevant_articles' && 'Релевантные статьи не найдены. Попробуйте другой запрос.'}
                {msg.status === 'retrieval_unavailable' && 'Поиск временно недоступен'}
              </Alert>
            )}

            {msg.sources && msg.sources.length > 0 && (
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="caption" color="text.secondary">Источники:</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {msg.sources.map((s) => (
                    <Chip
                      key={s.article_id}
                      label={s.title.length > 40 ? s.title.slice(0, 40) + '…' : s.title}
                      size="small"
                      variant="outlined"
                      onClick={() => onSourceClick?.(s.article_id)}
                      component="button"
                      aria-label={`Открыть статью: ${s.title}`}
                      sx={{ cursor: 'pointer', maxWidth: 250 }}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {msg.entities && msg.entities.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" color="text.secondary">Сущности:</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {msg.entities.map((e) => (
                    <Chip
                      key={e.name}
                      label={e.name}
                      size="small"
                      color={
                        e.type === 'PERSON' ? 'primary' :
                        e.type === 'ORGANIZATION' ? 'secondary' : 'default'
                      }
                    />
                  ))}
                </Box>
              </Box>
            )}

            {msg.retrievalDebug && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Вектор: {msg.retrievalDebug.vector_hits} | Граф: {msg.retrievalDebug.graph_hits}
                {msg.retrievalDebug.llm_model && ` | ${msg.retrievalDebug.llm_model}`}
              </Typography>
            )}
          </Paper>
        ))}

        {isLoading && (
          <Paper elevation={0} sx={{ p: 2, maxWidth: '90%', bgcolor: 'background.paper', borderRadius: 2 }}>
            <Skeleton width="80%" />
            <Skeleton width="60%" />
            <Skeleton width="40%" />
          </Paper>
        )}

        <div ref={messagesEndRef} />
      </Box>

      <Box
        component="form"
        onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
        sx={{ p: 2, borderTop: 1, borderColor: 'divider', display: 'flex', gap: 1 }}
      >
        <TextField
          inputRef={inputRef}
          fullWidth
          size="small"
          placeholder="Задайте вопрос..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          aria-label="Введите вопрос для поиска"
          slotProps={{ htmlInput: { 'aria-label': 'Поле ввода вопроса' } }}
        />
        <IconButton
          type="submit"
          color="primary"
          disabled={!input.trim() || isLoading}
          aria-label="Отправить вопрос"
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
}
