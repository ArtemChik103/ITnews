import { describe, it, expect } from 'vitest';
import { useFilterStore } from '../store/useFilterStore';

describe('useFilterStore', () => {
  it('has correct initial state', () => {
    const state = useFilterStore.getState();
    expect(state.source).toBe('');
    expect(state.language).toBe('');
    expect(state.dateFrom).toBe('');
    expect(state.dateTo).toBe('');
    expect(state.page).toBe(1);
    expect(state.pageSize).toBe(20);
    expect(state.sort).toBe('published_at');
  });

  it('setFilter updates field and resets page to 1', () => {
    const store = useFilterStore.getState();
    store.setPage(3);
    expect(useFilterStore.getState().page).toBe(3);

    store.setFilter('source', 'TechCrunch');
    const state = useFilterStore.getState();
    expect(state.source).toBe('TechCrunch');
    expect(state.page).toBe(1); // reset on filter change
  });

  it('resetFilters restores defaults', () => {
    const store = useFilterStore.getState();
    store.setFilter('source', 'Wired');
    store.setFilter('language', 'ru');
    store.setPage(5);

    store.resetFilters();
    const state = useFilterStore.getState();
    expect(state.source).toBe('');
    expect(state.language).toBe('');
    expect(state.page).toBe(1);
  });

  it('setPage updates page', () => {
    const store = useFilterStore.getState();
    store.setPage(7);
    expect(useFilterStore.getState().page).toBe(7);
  });
});
