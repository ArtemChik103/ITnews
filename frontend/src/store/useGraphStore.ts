import { create } from 'zustand';
import type { GraphNode, GraphEdge, SearchEntity } from '../types';

interface GraphStore {
  nodes: GraphNode[];
  edges: GraphEdge[];
  loading: boolean;
  setFromSearch: (edges: GraphEdge[], entities: SearchEntity[]) => void;
  setFromFetch: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useGraphStore = create<GraphStore>((set) => ({
  nodes: [],
  edges: [],
  loading: false,
  setFromSearch: (edges, entities) => {
    const nodes: GraphNode[] = entities.map((e) => ({
      id: e.name.toLowerCase().replace(/\s+/g, '_'),
      label: e.name,
      type: e.type,
      metadata: {},
    }));
    set({ nodes, edges, loading: false });
  },
  setFromFetch: (nodes, edges) => set({ nodes, edges, loading: false }),
  setLoading: (loading) => set({ loading }),
  clear: () => set({ nodes: [], edges: [], loading: false }),
}));
