import React from 'react';
import { Bot, Info } from 'lucide-react';

export function AgentPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <Bot className="w-5 h-5 text-accent" />
          Agent Activity
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Live view of GraphMind CLI Agent task execution
        </p>
      </div>

      <div className="panel border-status-warning/30 bg-status-warning/5">
        <div className="panel-body">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-status-warning shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-text-primary mb-0.5">Phase 6 — Not yet implemented</div>
              <p className="text-xs text-text-secondary leading-relaxed">
                The GraphMind CLI Agent will be built in Phase 6. It includes an Ollama-backed
                agent loop, file read/write/search tools, terminal execution, and GraphMind
                retrieval integration with a Rich-based terminal UI.
              </p>
              <div className="mt-2 code-block text-2xs">
                graphmind-agent ask "Explain the authentication flow"
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
