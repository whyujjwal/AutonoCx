import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  Channel,
  ChannelCreateRequest,
  ChannelUpdateRequest,
  ChannelTestResult,
} from '@/types/channel.types';
import type { ApiResponse, PaginatedResponse, PaginationParams } from '@/types/api.types';

export const channelsApi = {
  list(params?: PaginationParams) {
    return apiClient.get<ApiResponse<PaginatedResponse<Channel>>>(ENDPOINTS.CHANNELS, { params });
  },

  get(id: string) {
    return apiClient.get<ApiResponse<Channel>>(`${ENDPOINTS.CHANNELS}/${id}`);
  },

  create(data: ChannelCreateRequest) {
    return apiClient.post<ApiResponse<Channel>>(ENDPOINTS.CHANNELS, data);
  },

  update(id: string, data: ChannelUpdateRequest) {
    return apiClient.patch<ApiResponse<Channel>>(`${ENDPOINTS.CHANNELS}/${id}`, data);
  },

  delete(id: string) {
    return apiClient.delete(`${ENDPOINTS.CHANNELS}/${id}`);
  },

  test(id: string) {
    return apiClient.post<ApiResponse<ChannelTestResult>>(`${ENDPOINTS.CHANNELS}/${id}/test`);
  },
};
