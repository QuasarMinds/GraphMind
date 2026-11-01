import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import type { Core, ElementDefinition } from 'cytoscape';
import type { GraphNode, GraphEdge } from '../../types';

// ── Node type colors ─────────────────────────────────────────────────────────
const NODE_COLORS: Record<string, string> = {
  repository: '#4f7ef8',
  directory:  '#5c6289',
  file:       '#60a5fa',
  class:      '#a78bfa',
  function:   '#4caf7d',
  method:     '#34d399',
  import:     '#e8a44a',
  variable:   '#9399b2',
  interface:  '#f472b6',
  module:     '#fb923c',
};

const NODE_SHAPE: Record<string, string> = {
  repository: 'hexagon',
  directory:  'roundrectangle',
  file:       'roundrectangle',
  class:      'ellipse',
  function:   'ellipse',
  method:     'ellipse',
  import:     'diamond',
  variable:   'triangle',
  interface:  'ellipse',
  module:     'barrel',
};

// ── Edge colors ───────────────────────────────────────────────────────────────
const EDGE_COLORS: Record<string, string> = {
  CONTAINS:   '#2d3148',
  IMPORTS:    '#e8a44a',
  CALLS:      '#4caf7d',
  INHERITS:   '#a78bfa',
  IMPLEMENTS: '#f472b6',
  DEFINES:    '#4f7ef8',
  USES:       '#9399b2',
  DEPENDS_ON: '#e05c5c',
};

interface CytoscapeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect?: (node: GraphNode | null) => void;
  highlightedNodeIds?: Set<string>;
  className?: string;
}

export function CytoscapeGraph({
  nodes,
  edges,
  onNodeSelect,
  highlightedNodeIds,
  className = '',
}: CytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const buildElements = useCallback((): ElementDefinition[] => {
    const els: ElementDefinition[] = [];

    for (const n of nodes) {
      const color = NODE_COLORS[n.node_type] || '#9399b2';
      const isHighlighted = highlightedNodeIds?.has(n.id);
      els.push({
        group: 'nodes',
        data: {
          id: n.id,
          label: n.name.length > 20 ? n.name.slice(0, 18) + '…' : n.name,
          fullName: n.name,
          node_type: n.node_type,
          color,
          borderColor: isHighlighted ? '#ffffff' : color,
          ...n,
        },
      });
    }

    for (const e of edges) {
      // Only add edge if both source and target exist as nodes
      const srcExists = nodes.some((n) => n.id === e.source_id);
      const tgtExists = nodes.some((n) => n.id === e.target_id);
      if (!srcExists || !tgtExists) continue;

      els.push({
        group: 'edges',
        data: {
          id: e.id || `${e.source_id}-${e.edge_type}-${e.target_id}`,
          source: e.source_id,
          target: e.target_id,
          edge_type: e.edge_type,
          color: EDGE_COLORS[e.edge_type] || '#2d3148',
          label: e.edge_type,
        },
      });
    }

    return els;
  }, [nodes, edges, highlightedNodeIds]);

  // ── Initialize cytoscape ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(),
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'border-color': 'data(borderColor)',
            'border-width': 1.5,
            label: 'data(label)',
            'font-size': 9,
            'font-family': 'JetBrains Mono, monospace',
            color: '#e8eaf0',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 4,
            'text-outline-color': '#0f1117',
            'text-outline-width': 1,
            width: 28,
            height: 28,
            shape: 'ellipse',
            'overlay-padding': 4,
          },
        },
        {
          selector: 'node[node_type = "repository"]',
          style: { width: 40, height: 40, shape: 'hexagon', 'border-width': 2, 'font-size': 10 },
        },
        {
          selector: 'node[node_type = "file"]',
          style: { shape: 'roundrectangle', width: 34, height: 22 },
        },
        {
          selector: 'node[node_type = "directory"]',
          style: { shape: 'roundrectangle', width: 30, height: 20, 'font-size': 8 },
        },
        {
          selector: 'node[node_type = "import"]',
          style: { shape: 'diamond', width: 20, height: 20 },
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#4f7ef8',
            'border-width': 2.5,
            'background-color': 'data(color)',
            'overlay-color': '#4f7ef8',
            'overlay-opacity': 0.1,
          },
        },
        {
          selector: 'node.highlighted',
          style: { 'border-color': '#ffffff', 'border-width': 2.5 },
        },
        {
          selector: 'node.dimmed',
          style: { opacity: 0.2 },
        },
        {
          selector: 'edge',
          style: {
            'line-color': 'data(color)',
            'target-arrow-color': 'data(color)',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.7,
            'curve-style': 'bezier',
            width: 1,
            opacity: 0.5,
          },
        },
        {
          selector: 'edge:selected',
          style: { opacity: 1, width: 1.5 },
        },
        {
          selector: 'edge.dimmed',
          style: { opacity: 0.05 },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: true,
        nodeRepulsion: () => 4500,
        edgeElasticity: () => 45,
        idealEdgeLength: () => 80,
        gravity: 0.3,
        numIter: 1000,
        fit: true,
        padding: 40,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.2,
      minZoom: 0.05,
      maxZoom: 5,
    });

    // ── Node selection ────────────────────────────────────────────────────
    cy.on('tap', 'node', (evt) => {
      const tapped = evt.target;
      const data = tapped.data() as GraphNode;

      // Dim everything, highlight neighborhood
      cy.elements().addClass('dimmed');
      const hood = tapped.closedNeighborhood();
      hood.removeClass('dimmed');
      hood.addClass('highlighted');
      tapped.removeClass('dimmed');

      onNodeSelect?.(data);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass('dimmed highlighted');
        onNodeSelect?.(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);  // Only run once

  // ── Update elements when data changes ────────────────────────────────────
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.elements().remove();
    cy.add(buildElements());
    cy.layout({ name: 'cose', animate: false, fit: true, padding: 40 } as cytoscape.LayoutOptions).run();
  }, [buildElements]);

  return (
    <div ref={containerRef} className={`w-full h-full bg-bg-base ${className}`} id="cy-container" />
  );
}

// ── Legend ────────────────────────────────────────────────────────────────────

export function GraphLegend() {
  const nodeTypes = [
    { type: 'repository', label: 'Repository' },
    { type: 'file',       label: 'File' },
    { type: 'class',      label: 'Class' },
    { type: 'function',   label: 'Function' },
    { type: 'method',     label: 'Method' },
    { type: 'import',     label: 'Import' },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {nodeTypes.map(({ type, label }) => (
        <div key={type} className="flex items-center gap-1.5">
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: NODE_COLORS[type] }}
          />
          <span className="text-xs text-text-muted">{label}</span>
        </div>
      ))}
    </div>
  );
}
