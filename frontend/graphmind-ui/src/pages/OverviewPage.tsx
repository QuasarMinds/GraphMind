import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Share2,
  FolderGit2,
  FileCode,
  GitBranch,
  Cpu,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { fetchStatus, fetchRepositories } from '../services/api';
import { useAppStore } from '../store';

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div className="stat-card hover:border-border-strong transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="stat-label">{label}</span>
        <div
          className={`w-7 h-7 rounded-md flex items-center justify-center ${accent || 'bg-accent/10'}`}
        >
          <Icon className="w-3.5 h-3.5 text-accent" />
        </div>
      </div>
      <div className="stat-value">{typeof value === 'number' ? value.toLocaleString() : value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-2">
        <Share2 className="w-8 h-8 text-accent" />
      </div>
      <h2 className="text-lg font-semibold text-text-primary">Welcome to GraphMind</h2>
      <p className="text-text-secondary max-w-sm text-sm leading-relaxed">
        GraphMind builds a Code Knowledge Graph from your repositories, enabling intelligent
        context management for AI coding agents.
      </p>
      <Link to="/repositories" className="btn-primary mt-2">
        <FolderGit2 className="w-4 h-4" />
        Add your first repository
      </Link>
    </div>
  );
}

export function OverviewPage() {
  const { setEngineStatus, setRepositories, engineConnected } = useAppStore();

  const statusQuery = useQuery({
    queryKey: ['engine-status'],
    queryFn: fetchStatus,
    refetchInterval: 10_000,
    retry: 1,
  });

  const reposQuery = useQuery({
    queryKey: ['repositories'],
    queryFn: fetchRepositories,
    enabled: engineConnected || statusQuery.isSuccess,
  });

  useEffect(() => {
    if (statusQuery.data) {
      setEngineStatus(statusQuery.data, true);
    } else if (statusQuery.isError) {
      setEngineStatus(null, false);
    }
  }, [statusQuery.data, statusQuery.isError, setEngineStatus]);

  useEffect(() => {
    if (reposQuery.data) setRepositories(reposQuery.data);
  }, [reposQuery.data, setRepositories]);

  const status = statusQuery.data;
  const repos = reposQuery.data ?? [];
  const isConnected = !!status;

  if (statusQuery.isError) {
    return (
      <div className="p-6">
        <div className="panel max-w-lg mx-auto">
          <div className="panel-body">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-status-warning shrink-0 mt-0.5" />
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">
                  Engine not reachable
                </h2>
                <p className="text-xs text-text-secondary leading-relaxed">
                  GraphMind API is not running. Start it with:
                </p>
                <div className="code-block mt-2 text-2xs">
                  uvicorn api.main:app --host 127.0.0.1 --port 7430
                </div>
                <p className="text-xs text-text-muted mt-2">
                  The UI will reconnect automatically when the engine starts.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          Connecting to engine...
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">System Overview</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            GraphMind Engine · Repository intelligence & context optimization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={isConnected ? 'status-dot-ok' : 'status-dot-error'} />
          <span className="text-xs text-text-secondary">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>

      {/* ── Stats grid ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Graph Nodes"
          value={status.node_count}
          icon={Share2}
          sub="Across all repositories"
        />
        <StatCard
          label="Relationships"
          value={status.edge_count}
          icon={GitBranch}
          sub="Edges in the knowledge graph"
        />
        <StatCard
          label="Repositories"
          value={status.repositories}
          icon={FolderGit2}
          sub="Indexed and ready"
        />
        <StatCard
          label="Engine"
          value={status.version}
          icon={Cpu}
          sub={`API ${status.api_version}`}
        />
      </div>

      {/* ── Main area: repos + capabilities ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ── Repositories ────────────────────────────────────────────────── */}
        <div className="lg:col-span-2 panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-accent" />
              Indexed Repositories
            </h2>
            <Link to="/repositories" className="btn-ghost text-xs">
              Manage <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="panel-body">
              <EmptyState />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {repos.map((repo) => (
                <div key={repo.id} className="px-4 py-3 hover:bg-bg-hover transition-colors">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-medium text-text-primary">{repo.name}</div>
                      <div className="text-xs font-mono text-text-muted mt-0.5 truncate max-w-xs">
                        {repo.path}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap justify-end">
                      {repo.language_stats &&
                        Object.entries(repo.language_stats).slice(0, 3).map(([lang, count]) => (
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
                            {lang} ({count})
                          </span>
                        ))}
                    </div>
                  </div>
                  {repo.total_files != null && (
                    <div className="text-xs text-text-muted mt-1">
                      {repo.total_files.toLocaleString()} files indexed
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Capabilities panel ──────────────────────────────────────────── */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">Engine Capabilities</h2>
          </div>
          <div className="panel-body space-y-3">
            {[
              { label: 'Tree-sitter parsing', ok: status.tree_sitter_available },
              { label: 'Python support', ok: status.tree_sitter_available },
              { label: 'JavaScript/TS support', ok: status.tree_sitter_available },
              { label: 'Keyword retrieval', ok: true },
              { label: 'Semantic retrieval', ok: false, note: 'Phase 4' },
              { label: 'Graph traversal', ok: true },
              { label: 'Context ledger', ok: false, note: 'Phase 5' },
              { label: 'CLI Agent', ok: false, note: 'Phase 6' },
            ].map(({ label, ok, note }) => (
              <div key={label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {ok ? (
                    <CheckCircle className="w-3.5 h-3.5 text-status-success" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-text-muted" />
                  )}
                  <span className={`text-xs ${ok ? 'text-text-secondary' : 'text-text-muted'}`}>
                    {label}
                  </span>
                </div>
                {note && <span className="badge-grey">{note}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Quick actions ─────────────────────────────────────────────────── */}
      <div className="panel">
        <div className="panel-header">
          <h2 className="text-sm font-semibold text-text-primary">Quick Actions</h2>
        </div>
        <div className="panel-body">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              { label: 'Add Repository', to: '/repositories', icon: FolderGit2 },
              { label: 'Explore Graph', to: '/graph', icon: Share2 },
              { label: 'Run Traversal', to: '/traversal', icon: GitBranch },
              { label: 'Query Retrieval', to: '/retrieval', icon: FileCode },
            ].map(({ label, to, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="btn-secondary flex-col h-16 justify-center gap-1.5"
              >
                <Icon className="w-4 h-4" />
                <span className="text-xs">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
