// API service layer — communicates with the GraphMind FastAPI backend

import axios from 'axios';
import type {
  EngineStatus,
  GraphEdge,
  GraphNode,
  GraphStats,
  Repository,
  RetrievalResult,
  TraversalStep,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:7430/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Status ─────────────────────────────────────────────────────────────────

export const fetchStatus = (): Promise<EngineStatus> =>
  api.get('/status').then((r) => r.data);

// ── Repositories ───────────────────────────────────────────────────────────

export const fetchRepositories = (): Promise<Repository[]> =>
  api.get('/repositories').then((r) => r.data);

export const addRepository = (path: string, forceReindex = false): Promise<Repository> =>
  api.post('/repositories', { path, force_reindex: forceReindex }).then((r) => r.data);

export const fetchRepository = (id: string): Promise<Repository> =>
  api.get(`/repositories/${id}`).then((r) => r.data);

export const fetchRepositoryStats = (id: string): Promise<GraphStats> =>
  api.get(`/repositories/${id}/stats`).then((r) => r.data);

export const fetchRepositoryFiles = (id: string, limit = 500, offset = 0) =>
  api.get(`/repositories/${id}/files`, { params: { limit, offset } }).then((r) => r.data);

export const fetchIndexingProgress = (id: string) =>
  api.get(`/repositories/${id}/progress`).then((r) => r.data);

// ── Graph ──────────────────────────────────────────────────────────────────

export const fetchGraphNodes = (
  repoId: string,
  nodeType?: string,
  limit = 500,
  offset = 0
): Promise<{ nodes: GraphNode[]; count: number }> =>
  api
    .get(`/graph/${repoId}/nodes`, { params: { node_type: nodeType, limit, offset } })
    .then((r) => r.data);

export const fetchGraphEdges = (
  repoId: string,
  edgeType?: string,
  limit = 2000,
  offset = 0
): Promise<{ edges: GraphEdge[]; count: number }> =>
  api
    .get(`/graph/${repoId}/edges`, { params: { edge_type: edgeType, limit, offset } })
    .then((r) => r.data);

export const fetchNodeDetail = (
  repoId: string,
  nodeId: string
): Promise<{ node: GraphNode; neighbors: GraphNode[] }> =>
  api.get(`/graph/${repoId}/node/${nodeId}`).then((r) => r.data);

export const traverseGraph = (
  repoId: string,
  params: {
    start_node_id: string;
    max_depth?: number;
    edge_types?: string[];
    max_nodes?: number;
  }
): Promise<TraversalStep[]> =>
  api.post(`/graph/${repoId}/traverse`, params).then((r) => r.data);

export const searchGraphNodes = (
  repoId: string,
  query: string,
  limit = 50
): Promise<{ results: GraphNode[]; count: number }> =>
  api.get(`/graph/${repoId}/search`, { params: { q: query, limit } }).then((r) => r.data);

// ── Retrieval ──────────────────────────────────────────────────────────────

export const queryRetrieval = (params: {
  query: string;
  repo_id: string;
  top_k?: number;
  methods?: string[];
}): Promise<RetrievalResult> =>
  api.post('/retrieval/query', params).then((r) => r.data);

export const fetchRetrievalMethods = () =>
  api.get('/retrieval/methods').then((r) => r.data);

// ── Error helper ───────────────────────────────────────────────────────────

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'An unknown error occurred.';
}

export const isApiReachable = async (): Promise<boolean> => {
  try {
    await fetchStatus();
    return true;
  } catch {
    return false;
  }
};
