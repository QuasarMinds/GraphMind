import React from 'react';
import { Settings } from 'lucide-react';
import { useAppStore } from '../store';

export function SettingsPage() {
  const { engineStatus } = useAppStore();

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent" />
          Settings
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">Engine configuration and API connection</p>
      </div>

      <div className="space-y-4">
        {/* API */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">API Connection</h2>
          </div>
          <div className="panel-body space-y-3">
            <div>
              <label className="text-xs text-text-muted block mb-1">Engine API URL</label>
              <div className="input font-mono text-sm select-all cursor-text bg-bg-base">
                {import.meta.env.VITE_API_URL || 'http://localhost:7430/api/v1'}
              </div>
              <p className="text-xs text-text-muted mt-1">
                Override with <code className="font-mono text-2xs">VITE_API_URL</code> env variable.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={engineStatus ? 'status-dot-ok' : 'status-dot-error'} />
              <span className="text-xs text-text-secondary">
                {engineStatus
                  ? `Connected — Engine v${engineStatus.version}`
                  : 'Not connected'}
              </span>
            </div>
          </div>
        </div>

        {/* Engine info */}
        {engineStatus && (
          <div className="panel">
            <div className="panel-header">
              <h2 className="text-sm font-semibold text-text-primary">Engine Info</h2>
            </div>
            <div className="panel-body">
              <table className="data-table w-full">
                <tbody>
                  {[
                    ['Version', engineStatus.version],
                    ['API Version', engineStatus.api_version],
                    ['Tree-sitter', engineStatus.tree_sitter_available ? 'Available' : 'Not available'],
                    ['Total Nodes', engineStatus.node_count.toLocaleString()],
                    ['Total Edges', engineStatus.edge_count.toLocaleString()],
                    ['Repositories', String(engineStatus.repositories)],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td className="text-text-muted text-xs">{k}</td>
                      <td className="font-mono text-xs text-text-primary">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Start instructions */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-text-primary">Starting the Engine</h2>
          </div>
          <div className="panel-body space-y-2">
            <p className="text-xs text-text-secondary">Run from the repository root:</p>
            <div className="code-block">
              {`# Install engine dependencies
pip install -e engine/

# Start the API server
uvicorn api.main:app --host 127.0.0.1 --port 7430 --reload`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
