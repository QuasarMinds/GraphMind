import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderGit2, Plus, RefreshCw, FileCode, ChevronRight } from 'lucide-react';
import { fetchRepositories, addRepository, fetchRepositoryStats } from '../services/api';
import { useAppStore } from '../store';
import type { Repository } from '../types';

function AddRepoForm({ onAdd }: { onAdd: () => void }) {
  const [path, setPath] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (p: string) => addRepository(p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      queryClient.invalidateQueries({ queryKey: ['engine-status'] });
      setPath('');
      setError('');
      onAdd();
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="panel mb-4">
      <div className="panel-header">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Plus className="w-4 h-4 text-accent" />
          Add Repository
        </h2>
      </div>
      <div className="panel-body">
        <p className="text-xs text-text-secondary mb-3">
          Enter the absolute path to a local repository directory. GraphMind will scan, parse,
          and index all supported source files.
        </p>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="/absolute/path/to/your/repo"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && path.trim() && mutation.mutate(path.trim())}
          />
          <button
            className="btn-primary whitespace-nowrap"
            onClick={() => path.trim() && mutation.mutate(path.trim())}
            disabled={mutation.isPending || !path.trim()}
          >
            {mutation.isPending ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Indexing...
              </>
            ) : (
              <>
                <Plus className="w-3.5 h-3.5" />
                Index
              </>
            )}
          </button>
        </div>
        {error && (
          <p className="text-xs text-status-error mt-2">{error}</p>
        )}
        {mutation.isPending && (
          <div className="mt-3">
            <div className="text-xs text-text-muted mb-1">Indexing repository...</div>
            <div className="progress-track">
              <div className="progress-fill animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RepoCard({
  repo,
  isSelected,
  onSelect,
}: {
  repo: Repository;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const statsQuery = useQuery({
    queryKey: ['repo-stats', repo.id],
    queryFn: () => fetchRepositoryStats(repo.id),
    enabled: isSelected,
  });

  return (
    <div
      className={`panel cursor-pointer transition-all duration-150 ${
        isSelected ? 'border-accent shadow-accent' : 'hover:border-border-strong'
      }`}
      onClick={onSelect}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-accent shrink-0" />
            <div className="font-medium text-sm text-text-primary truncate">{repo.name}</div>
          </div>
          <ChevronRight
            className={`w-4 h-4 text-text-muted transition-transform ${isSelected ? 'rotate-90' : ''}`}
          />
        </div>

        <div className="text-xs font-mono text-text-muted mb-3 truncate">{repo.path}</div>

        {/* Language stats */}
        {repo.language_stats && (
          <div className="flex flex-wrap gap-1 mb-2">
            {Object.entries(repo.language_stats).map(([lang, count]) => (
              <span
                key={lang}
                className={
                  lang === 'python'
                    ? 'badge-blue'
                    : lang === 'javascript'
                    ? 'badge-amber'
                    : lang === 'typescript'
                    ? 'badge-purple'
                    : 'badge-grey'
                }
              >
                {lang}: {count}
              </span>
            ))}
          </div>
        )}

        {repo.total_files != null && (
          <div className="text-xs text-text-muted">{repo.total_files.toLocaleString()} files</div>
        )}

        {/* Expanded stats */}
        {isSelected && statsQuery.data && (
          <div className="mt-3 pt-3 border-t border-border grid grid-cols-3 gap-3">
            <div className="text-center">
              <div className="text-base font-semibold text-text-primary">
                {statsQuery.data.total_nodes.toLocaleString()}
              </div>
              <div className="text-2xs text-text-muted">Nodes</div>
            </div>
            <div className="text-center">
              <div className="text-base font-semibold text-text-primary">
                {statsQuery.data.total_edges.toLocaleString()}
              </div>
              <div className="text-2xs text-text-muted">Edges</div>
            </div>
            <div className="text-center">
              <div className="text-base font-semibold text-text-primary">
                {statsQuery.data.parse_errors}
              </div>
              <div className="text-2xs text-text-muted">Errors</div>
            </div>
          </div>
        )}

        {isSelected && statsQuery.data && (
          <div className="mt-2 pt-2 space-y-1">
            {Object.entries(statsQuery.data.node_counts).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between text-xs">
                <span className="text-text-muted capitalize">{type}</span>
                <span className="font-mono text-text-secondary">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function RepositoriesPage() {
  const [showForm, setShowForm] = useState(false);
  const { selectedRepoId, setSelectedRepo } = useAppStore();

  const reposQuery = useQuery({
    queryKey: ['repositories'],
    queryFn: fetchRepositories,
    refetchInterval: 5000,
  });

  const repos = reposQuery.data ?? [];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Repositories</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Manage indexed repositories and view their graph statistics
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-secondary"
            onClick={() => reposQuery.refetch()}
            disabled={reposQuery.isFetching}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reposQuery.isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            <Plus className="w-3.5 h-3.5" />
            Add Repository
          </button>
        </div>
      </div>

      {showForm && <AddRepoForm onAdd={() => setShowForm(false)} />}

      {repos.length === 0 && !reposQuery.isLoading ? (
        <div className="empty-state">
          <FolderGit2 className="empty-icon" />
          <p className="text-sm text-text-secondary">No repositories indexed yet.</p>
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="w-4 h-4" />
            Add your first repository
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {repos.map((repo) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              isSelected={selectedRepoId === repo.id}
              onSelect={() =>
                setSelectedRepo(selectedRepoId === repo.id ? null : repo.id)
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
