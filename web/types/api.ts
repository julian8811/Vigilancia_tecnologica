// ─── Auth ────────────────────────────────────────────────
// Tokens are now in httpOnly cookies — they never reach JavaScript.
// LoginRequest/RegisterRequest carry the same shape as the API
// expects in the request body.
export interface LoginRequest {
  email: string;
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
  | "tecnologica"
  | "cientifica"
  | "competitiva"
  | "patentaria"
  | "normativa"
  | "mercado"
  | "academica"
  | "mixta"
  | "estrategica";

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
  keywords_en?: string;
  keywords_es?: string;
  synonyms?: string;
  excluded_terms?: string;
  sources_selected?: string;
  boolean_queries?: string;
  scrape_urls?: string;
  generated_by_ai: boolean;
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
  project_id?: string;
  total_documents: number;
  extracted_documents?: number;
  pending_documents?: number;
  failed_documents?: number;
  corpus_ready: boolean;
  corpus_path?: string;
  corpus_size_bytes?: number;
  entries?: CorpusEntry[];
  last_rebuild_at?: string;
  status?: string;
  last_rebuilt?: string;
  file_count?: number;
}

export interface CorpusEntry {
  document_id: string;
  title?: string;
  file_type?: string;
  file_path?: string;
  text_path?: string;
  processing_status?: string;
  in_corpus?: boolean;
}

// ─── Graph ───────────────────────────────────────────────
export interface GraphRun {
  id: string;
  project_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  finished_at?: string;
  error_message?: string;
  node_count?: number;
  edge_count?: number;
  stats?: Record<string, any>;
}

export interface GraphNode {
  id: string;
  run_id: string;
  external_node_id: string;
  label: string;
  node_type: string;
  community_id?: number;
  centrality_score?: number;
  metadata_json: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  run_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  weight: number;
  metadata_json: Record<string, any>;
}

// ─── Analysis ─────────────────────────────────────────────
export interface Technology {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  category?: string;
  trl_level?: number;
  confidence?: number;
  evidence_score?: number;
  created_at: string;
}

export interface TechnologyListResponse {
  items: Technology[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Trend {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  momentum?: string;
  trend_type?: string;
  growth_signal?: string;
  created_at: string;
}

export interface TrendListResponse {
  items: Trend[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ActorAnalysis {
  id: string;
  project_id: string;
  name: string;
  actor_type?: string;
  country?: string;
  relevance?: number;
  created_at: string;
}

export interface ActorListResponse {
  items: ActorAnalysis[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Opportunity {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  opportunity_type?: string;
  potential?: string;
  effort?: string;
  priority?: string;
  created_at: string;
}

export interface OpportunityListResponse {
  items: Opportunity[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Reports ──────────────────────────────────────────────
export interface Report {
  id: string;
  project_id: string;
  title: string;
  report_type: string;
  status: string;
  format?: string;
  html_path?: string;
  pdf_path?: string;
  markdown_path?: string;
  error_message?: string;
  generated_at?: string;
  created_at: string;
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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
