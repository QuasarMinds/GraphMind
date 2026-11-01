import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { GitBranch, Play, RotateCcw, ChevronRight } from 'lucide-react';
import { fetchGraphNodes, traverseGraph } from '../services/api';
import { useAppStore } from '../store';
import type { GraphNode, TraversalStep } from '../types';

const EDGE_TYPES = ['CONTAINS','IMPORTS','CALLS','INHERITS','IMPLEMENTS','DEFINES','USES','DEPENDS_ON'];

const DEPTH_COLORS = [
  'bg-accent/20 border-accent/40 text-accent',
  'bg-purple-500/20 border-purple-500/40 text-purple-400',
  'bg-status-success/20 border-status-success/40 text-status-success',
  'bg-status-warning/20 border-status-warning/40 text-status-warning',
  'bg-status-error/20 border-status-error/40 text-status-error',
];

function TraversalStepRow({ step, index }: { step: TraversalStep; index: number }) {
  const depthStyle = DEPTH_COLORS[Math.min(step.depth, DEPTH_COLORS.length - 1)];
  return (
    <div
      className="flex items-start gap-3 py-2 px-3 hover:bg-bg-hover transition-colors rounded-md animate-fade-in"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <div
        className={`flex-shrink-0 w-6 h-6 rounded border text-xs font-mono flex items-center justify-center ${depthStyle}`}
      >
        {step.depth}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary truncate">
            {step.node.name}
          </span>
          <span className="badge-grey shrink-0">{step.node.node_type}</span>
          {step.via_edge_type && (
            <span className="badge-green shrink-0 font-mono text-2xs">{step.via_edge_type}</span>
          )}
        </div>
        {step.node.path && (
          <div className="text-xs text-text-muted font-mono truncate mt-0.5">{step.node.path}</div>
        )}
      </div>
    </div>
  );
}

export function TraversalPage() {
  const { selectedRepoId, repositories } = useAppStore();
  const [startNodeId, setStartNodeId] = useState('');
  const [maxDepth, setMaxDepth] = useState(3);
  const [maxNodes, setMaxNodes] = useState(80);
  const [selectedEdgeTypes, setSelectedEdgeTypes] = useState<string[]>([]);
  const [nodeSearch, setNodeSearch] = useState('');

  const repo = repositories.find((r) => r.id === selectedRepoId);

  // Load top-level nodes for the start-node selector
  const nodesQuery = useQuery({
    queryKey: ['graph-nodes-all', selectedRepoId],
    queryFn: () => fetchGraphNodes(selectedRepoId!, undefined, 300),
    enabled: !!selectedRepoId,
  });

  const filteredNodes = (nodesQuery.data?.nodes ?? []).filter(
    (n) =>
      n.node_type !== 'directory' &&
      (nodeSearch === '' || n.name.toLowerCase().includes(nodeSearch.toLowerCase()))
  );

  const traversalMut = useMutation({
    mutationFn: () =>
      traverseGraph(selectedRepoId!, {
        start_node_id: startNodeId,
        max_depth: maxDepth,
        max_nodes: maxNodes,
        edge_types: selectedEdgeTypes.length > 0 ? selectedEdgeTypes : undefined,
      }),
  });

  const steps = traversalMut.data ?? [];

  const toggleEdgeType = (t: string) =>
    setSelectedEdgeTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );

  if (!selectedRepoId) {
    return (
      <div className="empty-state h-full">
        <GitBranch className="empty-icon" />
        <p className="text-sm text-text-secondary">Select a repository to run graph traversals.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-accent" />
          Graph Traversal
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          BFS traversal from any node in{' '}
          <span className="font-medium text-text-primary">{repo?.name}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ── Config panel ─────────────────────────────────────────────── */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">Traversal Config</h2>
          </div>
          <div className="panel-body space-y-4">

            {/* Start node */}
            <div>
              <label className="text-xs text-text-muted mb-1.5 block">Start Node</label>
              <input
                className="input text-xs mb-1.5"
                placeholder="Search nodes…"
                value={nodeSearch}
                onChange={(e) => setNodeSearch(e.target.value)}
              />
              <div className="bg-bg-base border border-border rounded-md max-h-40 overflow-y-auto">
                {filteredNodes.slice(0, 40).map((n) => (
                  <button
                    key={n.id}
                    onClick={() => setStartNodeId(n.id)}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-bg-hover transition-colors flex items-center gap-2 ${
                      startNodeId === n.id ? 'bg-accent/10 text-accent' : 'text-text-secondary'
                    }`}
                  >
                    <span className="badge-grey shrink-0">{n.node_type}</span>
                    <span className="truncate">{n.name}</span>
                  </button>
                ))}
                {filteredNodes.length === 0 && (
                  <div className="px-3 py-4 text-xs text-text-muted text-center">No nodes found</div>
                )}
              </div>
              {startNodeId && (
                <div className="mt-1 text-2xs font-mono text-text-muted truncate">{startNodeId}</div>
              )}
            </div>

            {/* Depth */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-text-muted">Max Depth</label>
                <span className="text-xs font-mono text-text-primary">{maxDepth}</span>
              </div>
              <input
                type="range" min={1} max={8} value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="w-full accent-accent"
              />
            </div>

            {/* Max nodes */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-text-muted">Max Nodes</label>
                <span className="text-xs font-mono text-text-primary">{maxNodes}</span>
              </div>
              <input
                type="range" min={10} max={300} step={10} value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="w-full accent-accent"
              />
            </div>

            {/* Edge types */}
            <div>
              <label className="text-xs text-text-muted mb-1.5 block">
                Edge Types <span className="text-2xs">(all if none selected)</span>
              </label>
              <div className="flex flex-wrap gap-1.5">
                {EDGE_TYPES.map((t) => (
                  <button
                    key={t}
                    onClick={() => toggleEdgeType(t)}
                    className={`badge cursor-pointer transition-all text-2xs ${
                      selectedEdgeTypes.includes(t) ? 'badge-green' : 'badge-grey opacity-50 hover:opacity-100'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              <button
                className="btn-primary flex-1"
                onClick={() => traversalMut.mutate()}
                disabled={!startNodeId || traversalMut.isPending}
              >
                {traversalMut.isPending ? (
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                Traverse
              </button>
              <button
                className="btn-secondary"
                onClick={() => { traversalMut.reset(); setStartNodeId(''); }}
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* ── Results ────────────────────────────────────────────────────── */}
        <div className="lg:col-span-2 panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">
              Traversal Results
              {steps.length > 0 && (
                <span className="ml-2 text-text-muted font-normal">({steps.length} nodes visited)</span>
              )}
            </h2>
            {steps.length > 0 && (
              <div className="flex gap-2 text-xs text-text-muted">
                {[...new Set(steps.map((s) => s.depth))].map((d) => (
                  <span key={d} className={`badge ${DEPTH_COLORS[Math.min(d, DEPTH_COLORS.length-1)]}`}>
                    depth {d}: {steps.filter((s) => s.depth === d).length}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="panel-body">
            {steps.length === 0 && !traversalMut.isPending && (
              <div className="empty-state py-10">
                <GitBranch className="w-8 h-8 text-text-muted" />
                <p className="text-sm text-text-secondary">
                  Configure traversal parameters and click <strong>Traverse</strong>.
                </p>
              </div>
            )}

            {traversalMut.isPending && (
              <div className="flex items-center justify-center py-10">
                <div className="flex flex-col items-center gap-2 text-text-muted text-sm">
                  <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                  Traversing graph…
                </div>
              </div>
            )}

            {steps.length > 0 && (
              <div className="space-y-0.5">
                {steps.map((step, i) => (
                  <TraversalStepRow key={`${step.node.id}-${i}`} step={step} index={i} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
