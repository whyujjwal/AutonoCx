import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type { AuditLogEntry, AuditLogFilters } from '@/types/channel.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const auditApi = {
  list(params?: PaginationParams & AuditLogFilters) {
    return apiClient.get<ApiResponse<PaginatedResponse<AuditLogEntry>>>(ENDPOINTS.AUDIT, {
      params,
    });
  },

  export(params?: AuditLogFilters) {
    return apiClient.get(`${ENDPOINTS.AUDIT}/export`, {
      params,
      responseType: 'blob',
    });
  },
};
