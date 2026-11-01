import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search, ArrowRight, Info, Zap } from 'lucide-react';
import { queryRetrieval } from '../services/api';
import { useAppStore } from '../store';
import type { GraphNode } from '../types';

function ResultRow({ node, rank }: { node: GraphNode; rank: number }) {
  const typeColors: Record<string, string> = {
    file: 'badge-blue', class: 'badge-purple', function: 'badge-green',
    method: 'badge-green', import: 'badge-amber', variable: 'badge-grey',
  };
  return (
    <div className="flex items-start gap-3 py-2.5 px-3 hover:bg-bg-hover rounded-md transition-colors">
      <div className="w-6 h-6 rounded bg-bg-base border border-border flex items-center justify-center text-xs font-mono text-text-muted shrink-0">
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-medium text-text-primary truncate">{node.name}</span>
          <span className={typeColors[node.node_type] || 'badge-grey'}>{node.node_type}</span>
          {node.language && <span className="badge-grey">{node.language}</span>}
        </div>
        {node.path && (
          <div className="text-xs font-mono text-text-muted truncate">{node.path}</div>
        )}
        {node.start_line != null && (
          <div className="text-xs text-text-muted mt-0.5">
            Lines {node.start_line}–{node.end_line}
          </div>
        )}
      </div>
    </div>
  );
}

export function RetrievalPage() {
  const { selectedRepoId, repositories } = useAppStore();
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(20);

  const repo = repositories.find((r) => r.id === selectedRepoId);

  const mutation = useMutation({
    mutationFn: () =>
      queryRetrieval({ query, repo_id: selectedRepoId!, top_k: topK }),
  });

  const results = mutation.data?.results ?? [];

  if (!selectedRepoId) {
    return (
      <div className="empty-state h-full">
        <Search className="empty-icon" />
        <p className="text-sm text-text-secondary">Select a repository to explore retrieval.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <Search className="w-5 h-5 text-accent" />
          Retrieval Explorer
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Query the Code Knowledge Graph for relevant symbols in{' '}
          <span className="font-medium text-text-primary">{repo?.name}</span>
        </p>
      </div>

      {/* ── Query panel ───────────────────────────────────────────────────── */}
      <div className="panel mb-4">
        <div className="panel-header">
          <h2 className="text-sm font-semibold text-text-primary">Query</h2>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Info className="w-3.5 h-3.5" />
            Phase 1: keyword retrieval. Full hybrid in Phase 4.
          </div>
        </div>
        <div className="panel-body space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                className="input pl-10"
                placeholder='e.g. "authentication flow" or "parse_function"'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) =>
                  e.key === 'Enter' && query.trim() && selectedRepoId && mutation.mutate()
                }
              />
            </div>
            <button
              className="btn-primary"
              onClick={() => mutation.mutate()}
              disabled={!query.trim() || mutation.isPending}
            >
              {mutation.isPending ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
              Search
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-xs text-text-muted">Top K</label>
              <input
                type="number"
                min={5} max={100} value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="input w-16 text-xs py-1"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">Methods active:</span>
              <span className="badge-blue">keyword</span>
              <span className="badge-grey opacity-40">semantic</span>
              <span className="badge-grey opacity-40">graph</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Results ──────────────────────────────────────────────────────── */}
      <div className="panel">
        <div className="panel-header">
          <h2 className="text-sm font-semibold text-text-primary">
            Results
            {results.length > 0 && (
              <span className="ml-2 text-text-muted font-normal">({results.length})</span>
            )}
          </h2>
          {mutation.data?.note && (
            <div className="text-xs text-status-warning flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {mutation.data.note}
            </div>
          )}
        </div>
        <div className="panel-body p-0">
          {results.length === 0 && !mutation.isPending && !mutation.isError && (
            <div className="empty-state py-10">
              <Search className="w-8 h-8 text-text-muted" />
              <p className="text-sm text-text-secondary">Enter a query to retrieve relevant code symbols.</p>
            </div>
          )}
          {mutation.isError && (
            <div className="px-4 py-3 text-sm text-status-error">
              {String(mutation.error)}
            </div>
          )}
          <div className="divide-y divide-border/50">
            {results.map((r, i) => (
              <ResultRow key={r.id || i} node={r} rank={i + 1} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
