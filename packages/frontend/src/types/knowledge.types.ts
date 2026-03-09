/** Types matching the backend's actual response shapes (snake_case). */

export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'failed';

export interface KnowledgeBase {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  embedding_model: string | null;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  total_chunks: number;
  is_active: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface KBDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  content_type: string | null;
  file_size_bytes: number;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface KBCreateRequest {
  name: string;
  description?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface KBSearchRequest {
  query: string;
  knowledge_base_ids?: string[];
  top_k?: number;
  similarity_threshold?: number;
}

export interface KBSearchResultItem {
  document_id: string;
  knowledge_base_id: string;
  chunk_index: number;
  content: string;
  similarity_score: number;
  document_filename: string;
  metadata: Record<string, unknown> | null;
}

export interface KBSearchResponse {
  query: string;
  results: KBSearchResultItem[];
  total_results: number;
}

export interface PaginatedKBs {
  items: KnowledgeBase[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginatedDocs {
  items: KBDocument[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
