import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ArticleList from '../components/ArticleList';
import type { ArticleRead } from '../types';

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const mockArticles: ArticleRead[] = [
  {
    id: 1,
    title: 'Test Article One',
    source: 'TechCrunch',
    url: 'http://example.com/1',
    language: 'en',
    embedding_status: 'ready',
    embedding_model: 'test',
    embedded_at: null,
    cluster_id: 5,
    clustered_at: null,
    embedding_error: null,
    published_at: '2025-03-20T10:00:00Z',
    ingested_at: '2025-03-20T10:00:00Z',
  },
  {
    id: 2,
    title: 'Test Article Two',
    source: 'Wired',
    url: 'http://example.com/2',
    language: 'ru',
    embedding_status: 'ready',
    embedding_model: 'test',
    embedded_at: null,
    cluster_id: null,
    clustered_at: null,
    embedding_error: null,
    published_at: '2025-03-19T10:00:00Z',
    ingested_at: '2025-03-19T10:00:00Z',
  },
];

describe('ArticleList', () => {
  it('renders empty state when no articles', () => {
    renderWithRouter(
      <ArticleList articles={[]} total={0} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.getByText('Статьи не найдены')).toBeInTheDocument();
  });

  it('renders article cards', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={2} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.getByText('Test Article One')).toBeInTheDocument();
    expect(screen.getByText('Test Article Two')).toBeInTheDocument();
    expect(screen.getByText('TechCrunch')).toBeInTheDocument();
    expect(screen.getByText('Wired')).toBeInTheDocument();
  });

  it('shows total count', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={2} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.getByText('Найдено: 2 статей')).toBeInTheDocument();
  });

  it('shows cluster badge when cluster_id present', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={2} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.getByText('Кластер 5')).toBeInTheDocument();
  });

  it('shows language chips', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={2} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.getByText('EN')).toBeInTheDocument();
    expect(screen.getByText('RU')).toBeInTheDocument();
  });

  it('renders loading skeletons when isLoading', () => {
    const { container } = renderWithRouter(
      <ArticleList articles={[]} total={0} page={1} pageSize={20} onPageChange={() => {}} isLoading={true} />
    );
    // MUI Skeleton renders span elements with specific classes
    const skeletons = container.querySelectorAll('.MuiSkeleton-root');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows pagination when total exceeds page size', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={50} page={1} pageSize={20} onPageChange={() => {}} />
    );
    // Should have pagination nav
    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();
  });

  it('does not show pagination when all items fit on one page', () => {
    renderWithRouter(
      <ArticleList articles={mockArticles} total={2} page={1} pageSize={20} onPageChange={() => {}} />
    );
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
