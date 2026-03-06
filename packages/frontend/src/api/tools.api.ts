import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export interface Tool {
  id: string;
  name: string;
  description: string;
  type: 'api' | 'function' | 'webhook';
  endpoint?: string;
  method?: string;
  headers?: Record<string, string>;
  bodyTemplate?: string;
  parameters: ToolParameter[];
  requiresApproval: boolean;
  riskLevel: 'low' | 'medium' | 'high';
  usageCount: number;
  lastUsedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: unknown;
}

export interface ToolCreateRequest {
  name: string;
  description: string;
  type: 'api' | 'function' | 'webhook';
  endpoint?: string;
  method?: string;
  headers?: Record<string, string>;
  bodyTemplate?: string;
  parameters: ToolParameter[];
  requiresApproval: boolean;
  riskLevel: 'low' | 'medium' | 'high';
}

export const toolsApi = {
  list(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<Tool>>>(ENDPOINTS.TOOLS, { params });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<Tool>>(`${ENDPOINTS.TOOLS}/${id}`);
  },

  create(data: ToolCreateRequest) {
    return apiClient.post<ApiResponse<Tool>>(ENDPOINTS.TOOLS, data);
  },

  update(id: string, data: Partial<ToolCreateRequest>) {
    return apiClient.patch<ApiResponse<Tool>>(`${ENDPOINTS.TOOLS}/${id}`, data);
  },

  delete(id: string) {
    return apiClient.delete(`${ENDPOINTS.TOOLS}/${id}`);
  },

  test(id: string, data: { parameters: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ result: unknown; latencyMs: number }>>(
      `${ENDPOINTS.TOOLS}/${id}/test`,
      data,
    );
  },
};
