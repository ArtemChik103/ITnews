import { create } from 'zustand';
import type { GraphNode, GraphEdge, SearchEntity } from '../types';

interface GraphStore {
  nodes: GraphNode[];
  edges: GraphEdge[];
  setFromSearch: (edges: GraphEdge[], entities: SearchEntity[]) => void;
  clear: () => void;
}

export const useGraphStore = create<GraphStore>((set) => ({
  nodes: [],
  edges: [],
  setFromSearch: (edges, entities) => {
    const nodes: GraphNode[] = entities.map((e) => ({
      id: e.name.toLowerCase().replace(/\s+/g, '_'),
      label: e.name,
      type: e.type,
      metadata: {},
    }));
    set({ nodes, edges });
  },
  clear: () => set({ nodes: [], edges: [] }),
}));
