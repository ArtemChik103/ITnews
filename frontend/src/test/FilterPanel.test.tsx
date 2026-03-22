import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import FilterPanel from '../components/FilterPanel';
import { useFilterStore } from '../store/useFilterStore';

vi.mock('../api/client', () => ({
  fetchMeta: vi.fn().mockResolvedValue({ sources: ['techcrunch.com', 'www.wired.com'], languages: ['en'] }),
}));

describe('FilterPanel', () => {
  it('renders all filter controls', () => {
    render(<FilterPanel />);
    expect(screen.getByLabelText('Источник')).toBeInTheDocument();
    expect(screen.getByLabelText('Язык')).toBeInTheDocument();
    expect(screen.getByLabelText('Дата от')).toBeInTheDocument();
    expect(screen.getByLabelText('Дата до')).toBeInTheDocument();
    expect(screen.getByLabelText('Сортировка')).toBeInTheDocument();
  });

  it('does not show reset button when no filters active', () => {
    useFilterStore.getState().resetFilters();
    render(<FilterPanel />);
    expect(screen.queryByText('Сбросить')).not.toBeInTheDocument();
  });
});
