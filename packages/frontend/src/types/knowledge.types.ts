export type DocumentStatus = 'processing' | 'indexed' | 'failed';
export type DocumentType = 'pdf' | 'txt' | 'md' | 'html' | 'csv' | 'json';

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  documentCount: number;
  totalChunks: number;
  totalSizeBytes: number;
  embeddingModel: string;
  createdAt: string;
  updatedAt: string;
}

export interface KBDocument {
  id: string;
  knowledgeBaseId: string;
  name: string;
  type: DocumentType;
  status: DocumentStatus;
  sizeBytes: number;
  chunkCount: number;
  uploadedAt: string;
  processedAt?: string;
  errorMessage?: string;
}

export interface KBCreateRequest {
  name: string;
  description: string;
  embeddingModel?: string;
}

export interface KBSearchRequest {
  query: string;
  topK?: number;
  threshold?: number;
}

export interface KBSearchResult {
  content: string;
  documentId: string;
  documentName: string;
  score: number;
  metadata: Record<string, unknown>;
}
