import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Share2, Filter, Search, RefreshCw, Info, X, ChevronDown,
} from 'lucide-react';
import { fetchGraphNodes, fetchGraphEdges } from '../services/api';
import { useAppStore } from '../store';
import { CytoscapeGraph, GraphLegend } from '../components/graph/CytoscapeGraph';
import type { GraphNode } from '../types';

const NODE_TYPES = ['repository','directory','file','class','function','method','import','variable'];
const EDGE_TYPES = ['CONTAINS','IMPORTS','CALLS','INHERITS','IMPLEMENTS','DEFINES','USES','DEPENDS_ON'];

function NodeDetail({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const colorMap: Record<string, string> = {
    repository:'badge-blue', file:'badge-blue', class:'badge-purple',
    function:'badge-green', method:'badge-green', import:'badge-amber',
    variable:'badge-grey', directory:'badge-grey',
  };
  return (
    <div className="panel w-72 shrink-0 overflow-y-auto">
      <div className="panel-header">
        <h3 className="text-sm font-semibold text-text-primary truncate">{node.name}</h3>
        <button onClick={onClose} className="btn-ghost p-1"><X className="w-3.5 h-3.5" /></button>
      </div>
      <div className="panel-body space-y-3 text-xs">
        <div className="flex items-center gap-2">
          <span className={colorMap[node.node_type] || 'badge-grey'}>{node.node_type}</span>
          {node.language && <span className="badge-blue">{node.language}</span>}
        </div>
        {node.path && (
          <div>
            <div className="text-text-muted mb-0.5">Path</div>
            <div className="font-mono text-text-secondary break-all">{node.path}</div>
          </div>
        )}
        {(node.start_line != null) && (
          <div>
            <div className="text-text-muted mb-0.5">Lines</div>
            <div className="font-mono text-text-secondary">
              {node.start_line} – {node.end_line}
            </div>
          </div>
        )}
        {node.symbol_count != null && (
          <div>
            <div className="text-text-muted mb-0.5">Symbols</div>
            <div className="font-mono text-text-secondary">{node.symbol_count}</div>
          </div>
        )}
        {node.size_bytes != null && (
          <div>
            <div className="text-text-muted mb-0.5">Size</div>
            <div className="font-mono text-text-secondary">
              {(node.size_bytes / 1024).toFixed(1)} KB
            </div>
          </div>
        )}
        {(node.bases as string[] | undefined)?.length ? (
          <div>
            <div className="text-text-muted mb-0.5">Inherits</div>
            <div className="flex flex-wrap gap-1">
              {(node.bases as string[]).map((b) => (
                <span key={b} className="badge-purple">{b}</span>
              ))}
            </div>
          </div>
        ) : null}
        {node.docstring && (
          <div>
            <div className="text-text-muted mb-0.5">Docstring</div>
            <div className="text-text-secondary italic leading-relaxed">
              {String(node.docstring).slice(0, 200)}
              {String(node.docstring).length > 200 && '…'}
            </div>
          </div>
        )}
        <div>
          <div className="text-text-muted mb-0.5">Node ID</div>
          <div className="font-mono text-text-muted text-2xs break-all">{node.id}</div>
        </div>
      </div>
    </div>
  );
}

export function CodeGraphPage() {
  const { selectedRepoId, repositories } = useAppStore();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string[]>([]);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState<string[]>([]);
  const [searchQ, setSearchQ] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const repo = repositories.find((r) => r.id === selectedRepoId);

  const nodesQuery = useQuery({
    queryKey: ['graph-nodes', selectedRepoId],
    queryFn: () => fetchGraphNodes(selectedRepoId!, undefined, 1500),
    enabled: !!selectedRepoId,
  });

  const edgesQuery = useQuery({
    queryKey: ['graph-edges', selectedRepoId],
    queryFn: () => fetchGraphEdges(selectedRepoId!, undefined, 5000),
    enabled: !!selectedRepoId,
  });

  const filteredNodes = useMemo(() => {
    let nodes = nodesQuery.data?.nodes ?? [];
    if (nodeTypeFilter.length > 0) {
      nodes = nodes.filter((n) => nodeTypeFilter.includes(n.node_type));
    }
    if (searchQ.trim()) {
      const q = searchQ.toLowerCase();
      nodes = nodes.filter((n) => n.name.toLowerCase().includes(q));
    }
    return nodes;
  }, [nodesQuery.data, nodeTypeFilter, searchQ]);

  const filteredEdges = useMemo(() => {
    let edges = edgesQuery.data?.edges ?? [];
    if (edgeTypeFilter.length > 0) {
      edges = edges.filter((e) => edgeTypeFilter.includes(e.edge_type));
    }
    return edges;
  }, [edgesQuery.data, edgeTypeFilter]);

  const toggleFilter = (list: string[], setList: (v: string[]) => void, value: string) => {
    setList(list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);
  };

  if (!selectedRepoId) {
    return (
      <div className="empty-state h-full">
        <Share2 className="empty-icon" />
        <p className="text-sm text-text-secondary">Select a repository from the sidebar to explore its Code Knowledge Graph.</p>
        <a href="/repositories" className="btn-primary text-sm">Go to Repositories</a>
      </div>
    );
  }

  const isLoading = nodesQuery.isLoading || edgesQuery.isLoading;

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-bg-surface shrink-0 flex-wrap">
        <div className="flex items-center gap-2 text-sm text-text-primary font-medium">
          <Share2 className="w-4 h-4 text-accent" />
          Code Graph
          {repo && <span className="text-text-muted font-normal">— {repo.name}</span>}
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
          <input
            className="input pl-8 py-1.5 text-xs"
            placeholder="Search nodes…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
          />
        </div>

        <button className="btn-secondary text-xs" onClick={() => setShowFilters((v) => !v)}>
          <Filter className="w-3.5 h-3.5" />
          Filter
          {(nodeTypeFilter.length + edgeTypeFilter.length) > 0 && (
            <span className="badge-blue ml-1">{nodeTypeFilter.length + edgeTypeFilter.length}</span>
          )}
        </button>

        <button
          className="btn-ghost text-xs"
          onClick={() => { nodesQuery.refetch(); edgesQuery.refetch(); }}
          disabled={isLoading}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>

        <div className="ml-auto text-xs text-text-muted">
          {filteredNodes.length.toLocaleString()} nodes · {filteredEdges.length.toLocaleString()} edges
        </div>
      </div>

      {/* ── Filter panel ──────────────────────────────────────────────────── */}
      {showFilters && (
        <div className="px-4 py-3 border-b border-border bg-bg-surface shrink-0 space-y-2 animate-slide-in">
          <div>
            <div className="text-xs text-text-muted mb-1.5">Node types</div>
            <div className="flex flex-wrap gap-1.5">
              {NODE_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => toggleFilter(nodeTypeFilter, setNodeTypeFilter, t)}
                  className={`badge cursor-pointer transition-all ${
                    nodeTypeFilter.includes(t) ? 'badge-blue' : 'badge-grey opacity-60 hover:opacity-100'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-text-muted mb-1.5">Edge types</div>
            <div className="flex flex-wrap gap-1.5">
              {EDGE_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => toggleFilter(edgeTypeFilter, setEdgeTypeFilter, t)}
                  className={`badge cursor-pointer transition-all ${
                    edgeTypeFilter.includes(t) ? 'badge-green' : 'badge-grey opacity-60 hover:opacity-100'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Main graph area ───────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-text-muted text-sm">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              Loading graph…
            </div>
          </div>
        ) : (
          <div className="flex-1 relative">
            <CytoscapeGraph
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeSelect={setSelectedNode}
              className="absolute inset-0"
            />
            {/* Legend overlay */}
            <div className="absolute bottom-3 left-3 panel px-3 py-2">
              <GraphLegend />
            </div>
            {/* Node count overlay */}
            {filteredNodes.length === 0 && !isLoading && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-text-muted text-sm">
                  No nodes match the current filters.
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Node detail panel ──────────────────────────────────────────── */}
        {selectedNode && (
          <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </div>
    </div>
  );
}
