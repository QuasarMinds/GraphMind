import React from 'react';
import { Layers, Clock, Info } from 'lucide-react';

// Phase 5 placeholder — Context Manager dashboard
export function ContextPage() {
  const levels = [
    { label: 'Full source (Level 3)',    count: 0, badge: 'badge-green',  desc: 'Complete source code in context' },
    { label: 'Summary (Level 2)',        count: 0, badge: 'badge-blue',   desc: 'Signature + docstring' },
    { label: 'Signature only (Level 1)', count: 0, badge: 'badge-amber',  desc: 'Name and type signature' },
    { label: 'Unloaded (Level 0)',       count: 0, badge: 'badge-grey',   desc: 'Not in active context' },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <Layers className="w-5 h-5 text-accent" />
          Context Manager
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Tracks which code entities are in the AI agent's context window
        </p>
      </div>

      {/* Phase notice */}
      <div className="panel mb-4 border-status-warning/30 bg-status-warning/5">
        <div className="panel-body">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-status-warning shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-text-primary mb-0.5">Phase 5 — Not yet implemented</div>
              <p className="text-xs text-text-secondary leading-relaxed">
                The Context Manager (Context Ledger, hash tracking, deduplication, delta tracking,
                compression levels, and graph-aware eviction) will be implemented in Phase 5.
                The architecture and data models are fully defined in <code className="font-mono text-2xs">engine/graphmind/context/</code>.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mock dashboard — clearly labelled as empty/placeholder state */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {levels.map(({ label, count, badge, desc }) => (
          <div key={label} className="stat-card opacity-50">
            <span className="stat-label">{label}</span>
            <div className="stat-value font-mono">{count}</div>
            <div className="stat-sub">{desc}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="panel opacity-50">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">Token Budget</h2>
          </div>
          <div className="panel-body">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-text-muted">Used / Budget</span>
              <span className="text-xs font-mono text-text-primary">0 / 16,000</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: '0%' }} />
            </div>
            <div className="text-xs text-text-muted mt-2">0% of context budget used</div>
          </div>
        </div>

        <div className="panel opacity-50">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Ledger Events
            </h2>
          </div>
          <div className="panel-body">
            <div className="empty-state py-6">
              <p className="text-xs text-text-muted">No ledger events yet</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
