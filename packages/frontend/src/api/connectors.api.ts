import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  ConnectorConfig,
  ConnectorAvailable,
  ConnectorHealthResponse,
  ConnectorOperation,
  ConnectorConfigureRequest,
} from '@/types/connector.types';

export const connectorsApi = {
  listAvailable() {
    return apiClient.get<ConnectorAvailable[]>(`${ENDPOINTS.CONNECTORS}/available`);
  },

  list() {
    return apiClient.get<ConnectorConfig[]>(ENDPOINTS.CONNECTORS);
  },

  configure(connectorType: string, data: ConnectorConfigureRequest) {
    return apiClient.post<ConnectorConfig>(
      `${ENDPOINTS.CONNECTORS}/${connectorType}/configure`,
      data,
    );
  },

  remove(connectorType: string) {
    return apiClient.delete(`${ENDPOINTS.CONNECTORS}/${connectorType}`);
  },

  test(connectorType: string) {
    return apiClient.post<ConnectorHealthResponse>(
      `${ENDPOINTS.CONNECTORS}/${connectorType}/test`,
    );
  },

  getOperations(connectorType: string) {
    return apiClient.get<ConnectorOperation[]>(
      `${ENDPOINTS.CONNECTORS}/${connectorType}/operations`,
    );
  },
};
