import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type { Conversation, ConversationDetail, ConversationFilters } from '@/types/conversation.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const conversationsApi = {
  list(params?: PaginationParams & ConversationFilters) {
    return apiClient.get<ApiResponse<PaginatedResponse<Conversation>>>(ENDPOINTS.CONVERSATIONS, {
      params,
    });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<ConversationDetail>>(`${ENDPOINTS.CONVERSATIONS}/${id}`);
  },

  create(data: { agentId: string; channel: string; customerEmail?: string }) {
    return apiClient.post<ApiResponse<Conversation>>(ENDPOINTS.CONVERSATIONS, data);
  },

  sendMessage(id: string, data: { content: string }) {
    return apiClient.post<ApiResponse<ConversationDetail>>(
      `${ENDPOINTS.CONVERSATIONS}/${id}/messages`,
      data,
    );
  },

  escalate(id: string, data: { reason: string }) {
    return apiClient.post<ApiResponse<Conversation>>(
      `${ENDPOINTS.CONVERSATIONS}/${id}/escalate`,
      data,
    );
  },

  resolve(id: string, data?: { note?: string }) {
    return apiClient.post<ApiResponse<Conversation>>(
      `${ENDPOINTS.CONVERSATIONS}/${id}/resolve`,
      data,
    );
  },
};
