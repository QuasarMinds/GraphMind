import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';

const PAGE_TITLES: Record<string, string> = {
  '/':           'Overview',
  '/repositories': 'Repositories',
  '/graph':      'Code Graph',
  '/traversal':  'Graph Traversal',
  '/retrieval':  'Retrieval Explorer',
  '/context':    'Context Manager',
  '/agent':      'Agent Activity',
  '/settings':   'Settings',
};

export function TopBar() {
  const location = useLocation();
  const { engineStatus, selectedRepoId, repositories } = useAppStore();
  const title = PAGE_TITLES[location.pathname] || 'GraphMind';
  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  return (
    <header className="flex items-center justify-between h-12 px-4 border-b border-border bg-bg-surface shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-text-primary">{title}</h1>
        {selectedRepo && (
          <>
            <span className="text-text-muted">/</span>
            <span className="text-sm text-text-secondary font-mono truncate max-w-xs">
              {selectedRepo.name}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-4">
        {engineStatus && (
          <div className="flex items-center gap-3 text-xs text-text-muted">
            <span>
              <span className="text-text-primary font-mono">{engineStatus.node_count.toLocaleString()}</span>{' '}
              nodes
            </span>
            <span>
              <span className="text-text-primary font-mono">{engineStatus.edge_count.toLocaleString()}</span>{' '}
              edges
            </span>
            <span>
              <span className="text-text-primary font-mono">{engineStatus.repositories}</span>{' '}
              repos
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
