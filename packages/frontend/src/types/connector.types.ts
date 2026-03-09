export interface ConnectorConfig {
  id: string;
  org_id: string;
  connector_type: string;
  display_name: string | null;
  is_active: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_health_check_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorAvailable {
  connector_type: string;
  display_name: string;
}

export interface ConnectorHealthResponse {
  connector_type: string;
  status: string;
  error: string | null;
}

export interface ConnectorOperation {
  name: string;
  display_name: string;
  description: string;
  parameters_schema: Record<string, unknown>;
  risk_level: string;
  requires_approval: boolean;
}

export interface ConnectorConfigureRequest {
  config: Record<string, string>;
  display_name?: string;
}
