import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  Action,
  ActionApproveRequest,
  ActionRejectRequest,
  ActionStats,
} from '@/types/action.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const actionsApi = {
  list(params?: PaginationParams & { status?: string; category?: string; riskLevel?: string }) {
    return apiClient.get<ApiResponse<PaginatedResponse<Action>>>(ENDPOINTS.ACTIONS, { params });
  },

  getPending(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<Action>>>(`${ENDPOINTS.ACTIONS}/pending`, {
      params,
    });
  },

  approve(id: string, data?: ActionApproveRequest) {
    return apiClient.post<ApiResponse<Action>>(`${ENDPOINTS.ACTIONS}/${id}/approve`, data);
  },

  reject(id: string, data: ActionRejectRequest) {
    return apiClient.post<ApiResponse<Action>>(`${ENDPOINTS.ACTIONS}/${id}/reject`, data);
  },

  getStats() {
    return apiClient.get<ApiResponse<ActionStats>>(`${ENDPOINTS.ACTIONS}/stats`);
  },
};
