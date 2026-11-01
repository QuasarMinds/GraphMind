// GraphMind shared TypeScript types

export interface Repository {
  id: string;
  name: string;
  path: string;
  total_files?: number;
  language_stats?: Record<string, number>;
}

export interface GraphNode {
  id: string;
  node_type: string;
  name: string;
  repo_id?: string;
  path?: string;
  language?: string;
  start_line?: number;
  end_line?: number;
  size_bytes?: number;
  parse_status?: string;
  symbol_count?: number;
  line_count?: number;
  bases?: string[];
  docstring?: string;
  [key: string]: unknown;
}

export interface GraphEdge {
  id?: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  confidence?: number;
}

export interface GraphStats {
  repo_id: string;
  total_nodes: number;
  total_edges: number;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
  languages: string[];
  indexed_at?: string;
  parse_errors: number;
  unsupported_files: number;
}

export interface EngineStatus {
  status: string;
  version: string;
  node_count: number;
  edge_count: number;
  repositories: number;
  tree_sitter_available: boolean;
  api_version: string;
}

export interface TraversalStep {
  node: GraphNode;
  depth: number;
  parent_id: string | null;
  via_edge_type: string | null;
}

export interface RetrievalResult {
  query: string;
  repo_id: string;
  methods_used: string[];
  results: GraphNode[];
  count: number;
  note?: string;
}

export type NodeType =
  | 'repository'
  | 'directory'
  | 'file'
  | 'class'
  | 'function'
  | 'method'
  | 'variable'
  | 'import'
  | 'interface'
  | 'module';

export type EdgeType =
  | 'CONTAINS'
  | 'IMPORTS'
  | 'CALLS'
  | 'INHERITS'
  | 'IMPLEMENTS'
  | 'DEFINES'
  | 'USES'
  | 'DEPENDS_ON';
