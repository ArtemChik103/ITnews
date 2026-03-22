import { useEffect, useRef, useCallback, useMemo } from 'react';
import cytoscape from 'cytoscape';
import { Box, Typography, Chip, Alert } from '@mui/material';
import type { GraphNode, GraphEdge } from '../types';

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (nodeId: string, label: string) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  selectedNode?: string | null;
}

const MAX_NODES = 50;
const MAX_EDGES = 80;

const TYPE_COLORS: Record<string, string> = {
  PERSON: '#60a5fa',
  ORGANIZATION: '#f472b6',
  LOCATION: '#34d399',
  Entity: '#a78bfa',
};

export default function GraphView({ nodes, edges, onNodeClick, selectedNode }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const isTruncated = nodes.length >= MAX_NODES || edges.length >= MAX_EDGES;

  const elements = useMemo(() => {
    const nodeEls = nodes.slice(0, MAX_NODES).map((n) => ({
      data: {
        id: n.id,
        label: n.label,
        type: n.type,
        color: TYPE_COLORS[n.type] || TYPE_COLORS.Entity,
      },
    }));

    const nodeIds = new Set(nodeEls.map((n) => n.data.id));

    const edgeEls = edges.slice(0, MAX_EDGES)
      .filter((e) => {
        const srcId = e.from.toLowerCase().replace(/\s+/g, '_');
        const tgtId = e.to.toLowerCase().replace(/\s+/g, '_');
        return nodeIds.has(srcId) && nodeIds.has(tgtId);
      })
      .map((e, i) => ({
        data: {
          id: `edge-${i}`,
          source: e.from.toLowerCase().replace(/\s+/g, '_'),
          target: e.to.toLowerCase().replace(/\s+/g, '_'),
          label: e.relation,
        },
      }));

    return [...nodeEls.map((n) => ({ group: 'nodes' as const, ...n })), ...edgeEls.map((e) => ({ group: 'edges' as const, ...e }))];
  }, [nodes, edges]);

  const initCy = useCallback(() => {
    if (!containerRef.current) return;

    cyRef.current?.destroy();

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            color: '#f1f5f9',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 30,
            height: 30,
            'border-width': 2,
            'border-color': 'rgba(255,255,255,0.2)',
            'text-max-width': '80px',
            'text-wrap': 'ellipsis',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#fff',
            width: 40,
            height: 40,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': 'rgba(148,163,184,0.4)',
            'target-arrow-color': 'rgba(148,163,184,0.4)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9px',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
      ],
      layout: { name: 'cose', animate: false, nodeRepulsion: () => 8000, idealEdgeLength: () => 100 },
      minZoom: 0.3,
      maxZoom: 3,
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      onNodeClick?.(node.id(), node.data('label'));
    });

    cyRef.current = cy;
  }, [elements, onNodeClick]);

  useEffect(() => {
    initCy();
    return () => { cyRef.current?.destroy(); };
  }, [initCy]);

  useEffect(() => {
    if (!cyRef.current || !selectedNode) return;
    const node = cyRef.current.getElementById(selectedNode);
    if (node.length) {
      cyRef.current.nodes().unselect();
      node.select();
      cyRef.current.animate({ center: { eles: node }, zoom: 1.5, duration: 300 });
    }
  }, [selectedNode]);

  if (nodes.length === 0) {
    return (
      <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'text.secondary' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body1">Граф пуст</Typography>
          <Typography variant="body2">Выполните поиск или выберите статью для отображения связей</Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', position: 'relative' }}>
      {isTruncated && (
        <Alert severity="info" sx={{ position: 'absolute', top: 8, left: 8, right: 8, zIndex: 10, py: 0 }}>
          Показана часть графа (макс. {MAX_NODES} узлов, {MAX_EDGES} связей)
        </Alert>
      )}
      <Box sx={{ position: 'absolute', bottom: 8, left: 8, zIndex: 10, display: 'flex', gap: 0.5 }}>
        {Object.entries(TYPE_COLORS).filter(([k]) => k !== 'Entity').map(([type, color]) => (
          <Chip key={type} label={type} size="small" sx={{ bgcolor: color, color: '#fff', fontSize: '10px' }} />
        ))}
      </Box>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} role="img" aria-label="Граф связей сущностей" />
    </Box>
  );
}
