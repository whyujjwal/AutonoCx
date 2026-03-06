/** Shared API response shapes */

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  error_code?: string;
  request_id?: string;
  validation_errors?: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  type: string;
}

export interface HealthCheckResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  services: {
    database: "up" | "down";
    redis: "up" | "down";
    llm: "up" | "down";
  };
}
