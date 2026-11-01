// Zustand global store for GraphMind UI state

import { create } from 'zustand';
import type { EngineStatus, Repository } from '../types';

interface AppState {
  // ── Engine ──────────────────────────────────────────────────────────────
  engineStatus: EngineStatus | null;
  engineConnected: boolean;
  setEngineStatus: (status: EngineStatus | null, connected: boolean) => void;

  // ── Repositories ─────────────────────────────────────────────────────────
  repositories: Repository[];
  selectedRepoId: string | null;
  setRepositories: (repos: Repository[]) => void;
  addRepository: (repo: Repository) => void;
  setSelectedRepo: (id: string | null) => void;

  // ── UI ────────────────────────────────────────────────────────────────────
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  currentPage: string;
  setCurrentPage: (page: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  engineStatus: null,
  engineConnected: false,
  setEngineStatus: (status, connected) =>
    set({ engineStatus: status, engineConnected: connected }),

  repositories: [],
  selectedRepoId: null,
  setRepositories: (repos) => set({ repositories: repos }),
  addRepository: (repo) => set((s) => ({ repositories: [...s.repositories, repo] })),
  setSelectedRepo: (id) => set({ selectedRepoId: id }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  currentPage: 'overview',
  setCurrentPage: (page) => set({ currentPage: page }),
}));
