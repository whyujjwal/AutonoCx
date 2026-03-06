import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type { User, UserRole } from '@/types/auth.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const usersApi = {
  list(params?: PaginationParams & { role?: UserRole }) {
    return apiClient.get<ApiResponse<PaginatedResponse<User>>>(ENDPOINTS.USERS, { params });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<User>>(`${ENDPOINTS.USERS}/${id}`);
  },

  create(data: { email: string; name: string; role: UserRole }) {
    return apiClient.post<ApiResponse<User>>(ENDPOINTS.USERS, data);
  },

  update(id: string, data: { name?: string; isActive?: boolean }) {
    return apiClient.patch<ApiResponse<User>>(`${ENDPOINTS.USERS}/${id}`, data);
  },

  changeRole(id: string, role: UserRole) {
    return apiClient.patch<ApiResponse<User>>(`${ENDPOINTS.USERS}/${id}/role`, { role });
  },
};
