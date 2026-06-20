// ─── Auth ────────────────────────────────────────────────
export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  organization_name?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ─── User / Org ──────────────────────────────────────────
export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

// ─── Collection Run ───────────────────────────────────────
export interface CollectionRun {
  id: string;
  project_id: string;
  source_name: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
  docs_found: number;
  docs_inserted: number;
  error_message: string | null;
  created_at: string;
}

export interface CollectionRunListResponse {
  items: CollectionRun[];
  total: number;
}

// ─── Project ─────────────────────────────────────────────
export type ProjectStatus =
  | "draft"
  | "collecting"
  | "processing"
  | "graph_ready"
  | "report_ready"
  | "archived"
  | "failed";

export type SurveillanceType =
  | "patent"
  | "scientific"
  | "news"
  | "social"
  | "full";

export interface Project {
  id: string;
  name: string;
  slug: string;
  topic: string;
  description: string;
  surveillance_type: SurveillanceType;
  language: string;
  status: ProjectStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectCreate {
  name: string;
  topic: string;
  description?: string;
  surveillance_type: SurveillanceType;
  language: string;
  slug?: string;
}

// ─── Search Strategy ─────────────────────────────────────
export interface SearchStrategy {
  id: string;
  project_id: string;
  keywords: string[];
  synonyms: Record<string, string[]>;
  sources_selected: string[];
  created_at: string;
  updated_at: string;
}

// ─── Document ────────────────────────────────────────────
export interface Document {
  id: string;
  project_id: string;
  title: string;
  file_type: string;
  file_path?: string;
  text_path?: string;
  checksum?: string;
  source_name?: string;
  processing_status: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Corpus ──────────────────────────────────────────────
export interface CorpusSummary {
  total_documents: number;
  status: string;
  last_rebuilt?: string;
  file_count: number;
}

// ─── Graph ───────────────────────────────────────────────
export interface GraphRun {
  id: string;
  project_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  stats?: Record<string, any>;
}

export interface GraphNode {
  id: string;
  run_id: string;
  node_id: string;
  label: string;
  node_type: string;
  community?: number;
  centrality?: number;
  metadata: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  run_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  weight: number;
  metadata: Record<string, any>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GraphQueryRequest {
  query: string;
  max_nodes?: number;
}

export interface GraphQueryResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  query: string;
}

// ─── Visualization helpers ──────────────────────────────
export interface CytoscapeNode extends GraphNode {}
export interface CytoscapeEdge extends GraphEdge {}

export interface GraphVisualizationData {
  nodes: CytoscapeNode[];
  edges: CytoscapeEdge[];
}
