import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  KnowledgeBase,
  KBDocument,
  KBCreateRequest,
  KBSearchRequest,
  KBSearchResult,
} from '@/types/knowledge.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const knowledgeApi = {
  listKBs(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<KnowledgeBase>>>(ENDPOINTS.KNOWLEDGE_BASES, {
      params,
    });
  },

  getKB(id: string) {
    return apiClient.get<ApiResponse<KnowledgeBase & { documents: KBDocument[] }>>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${id}`,
    );
  },

  createKB(data: KBCreateRequest) {
    return apiClient.post<ApiResponse<KnowledgeBase>>(ENDPOINTS.KNOWLEDGE_BASES, data);
  },

  uploadDocument(kbId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<ApiResponse<KBDocument>>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/documents`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
  },

  searchKB(kbId: string, data: KBSearchRequest) {
    return apiClient.post<ApiResponse<KBSearchResult[]>>(
      `${ENDPOINTS.KNOWLEDGE_BASES}/${kbId}/search`,
      data,
    );
  },
};
