import apiClient from './client';
import { ENDPOINTS } from '@/lib/constants';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  ForgotPasswordRequest,
  AuthTokens,
} from '@/types/auth.types';
import type { ApiResponse } from '@/types/api.types';

export const authApi = {
  login(data: LoginRequest) {
    return apiClient.post<ApiResponse<LoginResponse>>(ENDPOINTS.AUTH.LOGIN, data);
  },

  register(data: RegisterRequest) {
    return apiClient.post<ApiResponse<LoginResponse>>(ENDPOINTS.AUTH.REGISTER, data);
  },

  refreshToken(refreshToken: string) {
    return apiClient.post<ApiResponse<AuthTokens>>(ENDPOINTS.AUTH.REFRESH, { refreshToken });
  },

  logout() {
    return apiClient.post(ENDPOINTS.AUTH.LOGOUT);
  },

  forgotPassword(data: ForgotPasswordRequest) {
    return apiClient.post<ApiResponse<{ message: string }>>(ENDPOINTS.AUTH.FORGOT_PASSWORD, data);
  },
};
