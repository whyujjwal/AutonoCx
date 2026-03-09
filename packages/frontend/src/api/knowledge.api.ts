import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  KnowledgeBase,
  KBDocument,
  KBCreateRequest,
  KBSearchRequest,
  KBSearchResponse,
  PaginatedKBs,
  PaginatedDocs,
} from '@/types/knowledge.types';

export const knowledgeApi = {
  listKBs(params?: { page?: number; page_size?: number; is_active?: boolean }) {
    return apiClient.get<PaginatedKBs>(ENDPOINTS.KNOWLEDGE_BASES, { params });
  },

  getKB(id: string) {
    return apiClient.get<KnowledgeBase>(`${ENDPOINTS.KNOWLEDGE_BASES}/${id}`);
  },

  createKB(data: KBCreateRequest) {
    return apiClient.post<KnowledgeBase>(ENDPOINTS.KNOWLEDGE_BASES, data);
  },

  deleteKB(id: string) {
    return apiClient.delete(`${ENDPOINTS.KNOWLEDGE_BASES}/${id}`);
  },

  listDocuments(kbId: string, params?: { page?: number; page_size?: number }) {
    return apiClient.get<PaginatedDocs>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/documents`,
      { params },
    );
  },

  getDocument(kbId: string, docId: string) {
    return apiClient.get<KBDocument>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/documents/${docId}`,
    );
  },

  uploadDocument(kbId: string, file: File, onUploadProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<KBDocument>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/documents`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onUploadProgress
          ? (event) => {
              const percent = event.total ? Math.round((event.loaded * 100) / event.total) : 0;
              onUploadProgress(percent);
            }
          : undefined,
      },
    );
  },

  deleteDocument(kbId: string, docId: string) {
    return apiClient.delete(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/documents/${docId}`,
    );
  },

  search(data: KBSearchRequest) {
    return apiClient.post<KBSearchResponse>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/search`,
      data,
    );
  },
};
