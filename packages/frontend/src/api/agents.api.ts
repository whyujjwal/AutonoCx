import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  Agent,
  AgentCreateRequest,
  AgentUpdateRequest,
  AgentTestRequest,
  AgentTestResponse,
} from '@/types/agent.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const agentsApi = {
  list(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<Agent>>>(ENDPOINTS.AGENTS, { params });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<Agent>>(`${ENDPOINTS.AGENTS}/${id}`);
  },

  create(data: AgentCreateRequest) {
    return apiClient.post<ApiResponse<Agent>>(ENDPOINTS.AGENTS, data);
  },

  update(id: string, data: AgentUpdateRequest) {
    return apiClient.patch<ApiResponse<Agent>>(`${ENDPOINTS.AGENTS}/${id}`, data);
  },

  delete(id: string) {
    return apiClient.delete(`${ENDPOINTS.AGENTS}/${id}`);
  },

  test(id: string, data: AgentTestRequest) {
    return apiClient.post<ApiResponse<AgentTestResponse>>(`${ENDPOINTS.AGENTS}/${id}/test`, data);
  },
};
