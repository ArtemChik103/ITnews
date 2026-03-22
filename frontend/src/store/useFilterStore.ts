import { create } from 'zustand';
import type { FilterState } from '../types';

interface FilterStore extends FilterState {
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
}

const initialState: FilterState = {
  source: '',
  language: '',
  clusterId: '',
  dateFrom: '',
  dateTo: '',
  entityType: '',
  page: 1,
  pageSize: 20,
  sort: 'published_at',
};

export const useFilterStore = create<FilterStore>((set) => ({
  ...initialState,
  setFilter: (key, value) => set({ [key]: value, page: 1 }),
  resetFilters: () => set(initialState),
  setPage: (page) => set({ page }),
}));
