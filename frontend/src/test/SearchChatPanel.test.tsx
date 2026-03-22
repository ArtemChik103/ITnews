import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import SearchChatPanel from '../components/SearchChatPanel';

// Mock the API
vi.mock('../api/client', () => ({
  searchRAG: vi.fn(),
}));

import { searchRAG } from '../api/client';

const mockSearchRAG = vi.mocked(searchRAG);

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SearchChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state with prompt', () => {
    renderWithProviders(<SearchChatPanel />);
    expect(screen.getByText('Задайте вопрос о новостях')).toBeInTheDocument();
  });

  it('renders input field and send button', () => {
    renderWithProviders(<SearchChatPanel />);
    expect(screen.getByPlaceholderText('Задайте вопрос...')).toBeInTheDocument();
    expect(screen.getByLabelText('Отправить вопрос')).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    renderWithProviders(<SearchChatPanel />);
    const sendBtn = screen.getByLabelText('Отправить вопрос');
    expect(sendBtn).toBeDisabled();
  });

  it('sends message and displays response on success', async () => {
    const user = userEvent.setup();

    mockSearchRAG.mockResolvedValueOnce({
      answer: 'Test answer from RAG',
      sources: [{ article_id: 1, title: 'Source Article', url: 'http://example.com', source: 'TestSource' }],
      entities: [{ name: 'TestEntity', type: 'ORGANIZATION' }],
      graph_edges: [],
      retrieval_debug: { vector_hits: 3, graph_hits: 1, llm_provider: 'groq', llm_model: 'llama3', degraded_mode: null },
      confidence: 0.85,
      status: 'success',
    });

    renderWithProviders(<SearchChatPanel />);

    const input = screen.getByPlaceholderText('Задайте вопрос...');
    await user.type(input, 'What companies are in AI?');
    await user.keyboard('{Enter}');

    // User message should appear
    expect(screen.getByText('What companies are in AI?')).toBeInTheDocument();

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText('Test answer from RAG')).toBeInTheDocument();
    });

    // Sources displayed
    expect(screen.getByText(/Source Article/)).toBeInTheDocument();
    // Entity chip displayed
    expect(screen.getByText('TestEntity')).toBeInTheDocument();
  });

  it('shows error message when API call fails', async () => {
    const user = userEvent.setup();
    mockSearchRAG.mockRejectedValueOnce(new Error('Network error'));

    renderWithProviders(<SearchChatPanel />);

    const input = screen.getByPlaceholderText('Задайте вопрос...');
    await user.type(input, 'test question');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/Ошибка при получении ответа/)).toBeInTheDocument();
    });
  });

  it('shows degraded mode alert', async () => {
    const user = userEvent.setup();

    mockSearchRAG.mockResolvedValueOnce({
      answer: 'Degraded answer',
      sources: [],
      entities: [],
      graph_edges: [],
      retrieval_debug: { vector_hits: 2, graph_hits: 0, llm_provider: null, llm_model: null, degraded_mode: 'retrieval_only' },
      confidence: 0.3,
      status: 'degraded',
    });

    renderWithProviders(<SearchChatPanel />);

    const input = screen.getByPlaceholderText('Задайте вопрос...');
    await user.type(input, 'test');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('Degraded answer')).toBeInTheDocument();
      expect(screen.getByText(/деградации/)).toBeInTheDocument();
    });
  });

  it('calls onSourceClick when source chip is clicked', async () => {
    const user = userEvent.setup();
    const onSourceClick = vi.fn();

    mockSearchRAG.mockResolvedValueOnce({
      answer: 'Answer',
      sources: [{ article_id: 42, title: 'Clickable Source', url: 'http://example.com', source: 'Src' }],
      entities: [],
      graph_edges: [],
      retrieval_debug: { vector_hits: 1, graph_hits: 0, llm_provider: 'groq', llm_model: 'test', degraded_mode: null },
      confidence: 0.8,
      status: 'success',
    });

    renderWithProviders(<SearchChatPanel onSourceClick={onSourceClick} />);

    const input = screen.getByPlaceholderText('Задайте вопрос...');
    await user.type(input, 'test');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/Clickable Source/)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/Clickable Source/));
    expect(onSourceClick).toHaveBeenCalledWith(42);
  });
});
