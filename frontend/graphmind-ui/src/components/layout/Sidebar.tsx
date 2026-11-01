import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  Share2,
  GitBranch,
  Search,
  Layers,
  Bot,
  Settings,
  ChevronLeft,
  ChevronRight,
  Cpu,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAppStore } from '../../store';

interface NavItem {
  label: string;
  icon: React.ElementType;
  to: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview',          icon: LayoutDashboard, to: '/' },
  { label: 'Repositories',      icon: FolderGit2,      to: '/repositories' },
  { label: 'Code Graph',        icon: Share2,          to: '/graph' },
  { label: 'Graph Traversal',   icon: GitBranch,       to: '/traversal' },
  { label: 'Retrieval',         icon: Search,          to: '/retrieval' },
  { label: 'Context Manager',   icon: Layers,          to: '/context' },
  { label: 'Agent Activity',    icon: Bot,             to: '/agent' },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, engineConnected } = useAppStore();

  return (
    <aside
      className={clsx(
        'sidebar transition-all duration-200 ease-in-out',
        sidebarCollapsed ? 'w-14' : 'w-60'
      )}
    >
      {/* ── Brand ────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-border">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 shrink-0">
          <Share2 className="w-4 h-4 text-accent" />
        </div>
        {!sidebarCollapsed && (
          <div className="overflow-hidden">
            <div className="font-semibold text-text-primary text-sm leading-tight tracking-tight">
              GraphMind
            </div>
            <div className="text-2xs text-text-muted font-mono">v0.1.0</div>
          </div>
        )}
      </div>

      {/* ── Engine status ─────────────────────────────────────────────────── */}
      {!sidebarCollapsed && (
        <div className="px-3 py-2 mx-2 mt-2 rounded-md bg-bg-base border border-border flex items-center gap-2">
          <span className={engineConnected ? 'status-dot-ok' : 'status-dot-error'} />
          <span className="text-xs text-text-secondary">
            {engineConnected ? 'Engine connected' : 'Engine offline'}
          </span>
        </div>
      )}

      {/* ── Navigation ────────────────────────────────────────────────────── */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {!sidebarCollapsed && (
          <div className="nav-section-label">Navigation</div>
        )}
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              clsx(
                'nav-item',
                sidebarCollapsed && 'justify-center px-0',
                isActive && 'active'
              )
            }
            title={sidebarCollapsed ? item.label : undefined}
          >
            <item.icon className="w-4 h-4 shrink-0" />
            {!sidebarCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* ── Bottom ────────────────────────────────────────────────────────── */}
      <div className="border-t border-border px-2 py-2 space-y-0.5">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx('nav-item', sidebarCollapsed && 'justify-center px-0', isActive && 'active')
          }
          title={sidebarCollapsed ? 'Settings' : undefined}
        >
          <Settings className="w-4 h-4 shrink-0" />
          {!sidebarCollapsed && <span>Settings</span>}
        </NavLink>

        <button
          onClick={toggleSidebar}
          className="nav-item w-full"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
