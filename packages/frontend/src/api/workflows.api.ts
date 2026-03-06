import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  Workflow,
  WorkflowCreateRequest,
  WorkflowUpdateRequest,
} from '@/types/workflow.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const workflowsApi = {
  list(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<Workflow>>>(ENDPOINTS.WORKFLOWS, { params });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<Workflow>>(`${ENDPOINTS.WORKFLOWS}/${id}`);
  },

  create(data: WorkflowCreateRequest) {
    return apiClient.post<ApiResponse<Workflow>>(ENDPOINTS.WORKFLOWS, data);
  },

  update(id: string, data: WorkflowUpdateRequest) {
    return apiClient.patch<ApiResponse<Workflow>>(`${ENDPOINTS.WORKFLOWS}/${id}`, data);
  },

  delete(id: string) {
    return apiClient.delete(`${ENDPOINTS.WORKFLOWS}/${id}`);
  },

  activate(id: string) {
    return apiClient.post<ApiResponse<Workflow>>(`${ENDPOINTS.WORKFLOWS}/${id}/activate`);
  },
};
