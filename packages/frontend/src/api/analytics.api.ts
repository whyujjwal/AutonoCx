import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  DashboardMetrics,
  ConversationMetrics,
  CostBreakdown,
  AnalyticsFilters,
} from '@/types/analytics.types';
import type { ApiResponse } from '@/types/api.types';

export const analyticsApi = {
  getDashboard(params?: Partial<AnalyticsFilters>) {
    return apiClient.get<ApiResponse<DashboardMetrics>>(`${ENDPOINTS.ANALYTICS}/dashboard`, {
      params,
    });
  },

  getConversationMetrics(params?: AnalyticsFilters) {
    return apiClient.get<ApiResponse<ConversationMetrics>>(
      `${ENDPOINTS.ANALYTICS}/conversations`,
      { params },
    );
  },

  getCostBreakdown(params?: AnalyticsFilters) {
    return apiClient.get<ApiResponse<CostBreakdown>>(`${ENDPOINTS.ANALYTICS}/costs`, { params });
  },
};
