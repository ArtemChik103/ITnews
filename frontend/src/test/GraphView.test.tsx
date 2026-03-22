import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import GraphView from '../components/GraphView';
import type { GraphNode, GraphEdge } from '../types';

// Mock cytoscape since jsdom has no canvas
vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    destroy: vi.fn(),
    nodes: vi.fn(() => ({ unselect: vi.fn() })),
    getElementById: vi.fn(() => ({ length: 0, select: vi.fn() })),
    animate: vi.fn(),
  })),
}));

const mockNodes: GraphNode[] = [
  { id: 'elon_musk', label: 'Elon Musk', type: 'PERSON', metadata: {} },
  { id: 'tesla', label: 'Tesla', type: 'ORGANIZATION', metadata: {} },
  { id: 'spacex', label: 'SpaceX', type: 'ORGANIZATION', metadata: {} },
];

const mockEdges: GraphEdge[] = [
  { from: 'Elon Musk', relation: 'CEO_OF', to: 'Tesla', source_article_ids: [1] },
  { from: 'Elon Musk', relation: 'CEO_OF', to: 'SpaceX', source_article_ids: [2] },
];

describe('GraphView', () => {
  it('renders empty state when no nodes', () => {
    render(<GraphView nodes={[]} edges={[]} />);
    expect(screen.getByText('Граф пуст')).toBeInTheDocument();
  });

  it('renders graph container when nodes provided', () => {
    render(<GraphView nodes={mockNodes} edges={mockEdges} />);
    expect(screen.getByRole('img', { name: 'Граф связей сущностей' })).toBeInTheDocument();
  });

  it('shows legend chips for entity types', () => {
    render(<GraphView nodes={mockNodes} edges={mockEdges} />);
    expect(screen.getByText('PERSON')).toBeInTheDocument();
    expect(screen.getByText('ORGANIZATION')).toBeInTheDocument();
    expect(screen.getByText('LOCATION')).toBeInTheDocument();
  });

  it('shows truncation notice when at max capacity', () => {
    const manyNodes = Array.from({ length: 50 }, (_, i) => ({
      id: `node_${i}`,
      label: `Node ${i}`,
      type: 'Entity',
      metadata: {},
    }));
    render(<GraphView nodes={manyNodes} edges={[]} />);
    expect(screen.getByText(/Показана часть графа/)).toBeInTheDocument();
  });

  it('does not show truncation notice for small graphs', () => {
    render(<GraphView nodes={mockNodes} edges={mockEdges} />);
    expect(screen.queryByText(/Показана часть графа/)).not.toBeInTheDocument();
  });
});
