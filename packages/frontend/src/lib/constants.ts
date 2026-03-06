export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

export const ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    FORGOT_PASSWORD: '/auth/forgot-password',
  },
  CONVERSATIONS: '/conversations',
  AGENTS: '/agents',
  KNOWLEDGE_BASES: '/knowledge-bases',
  TOOLS: '/tools',
  ACTIONS: '/actions',
  WORKFLOWS: '/workflows',
  ANALYTICS: '/analytics',
  PROMPTS: '/prompts',
  CHANNELS: '/channels',
  AUDIT: '/audit',
  USERS: '/users',
} as const;

export const ROLES = {
  ADMIN: 'admin',
  MANAGER: 'manager',
  OPERATOR: 'operator',
  VIEWER: 'viewer',
} as const;

export const CONVERSATION_STATUS = {
  ACTIVE: 'active',
  WAITING: 'waiting',
  ESCALATED: 'escalated',
  RESOLVED: 'resolved',
  CLOSED: 'closed',
} as const;

export const ACTION_STATUS = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  EXPIRED: 'expired',
  AUTO_APPROVED: 'auto_approved',
} as const;

export const RISK_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;

export const CHANNEL_PROVIDERS = {
  WEB_WIDGET: 'web_widget',
  EMAIL: 'email',
  SLACK: 'slack',
  WHATSAPP: 'whatsapp',
  API: 'api',
  DISCORD: 'discord',
  TELEGRAM: 'telegram',
} as const;

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 25;
