import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type { PromptTemplate, PromptVersion, PromptCreateRequest } from '@/types/channel.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const promptsApi = {
  list(params?: PaginationParams & { category?: string }) {
    return apiClient.get<ApiResponse<PaginatedResponse<PromptTemplate>>>(ENDPOINTS.PROMPTS, {
      params,
    });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<PromptTemplate>>(`${ENDPOINTS.PROMPTS}/${id}`);
  },

  create(data: PromptCreateRequest) {
    return apiClient.post<ApiResponse<PromptTemplate>>(ENDPOINTS.PROMPTS, data);
  },

  createVersion(id: string, data: { content: string; changeNote: string }) {
    return apiClient.post<ApiResponse<PromptVersion>>(
      `${ENDPOINTS.PROMPTS}/${id}/versions`,
      data,
    );
  },

  publish(id: string, versionId: string) {
    return apiClient.post<ApiResponse<PromptTemplate>>(
      `${ENDPOINTS.PROMPTS}/${id}/versions/${versionId}/publish`,
    );
  },

  rollback(id: string, versionId: string) {
    return apiClient.post<ApiResponse<PromptTemplate>>(
      `${ENDPOINTS.PROMPTS}/${id}/versions/${versionId}/rollback`,
    );
  },
};
