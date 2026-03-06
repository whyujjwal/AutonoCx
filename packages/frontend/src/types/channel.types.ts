export type ChannelStatus = 'active' | 'inactive' | 'error';
export type ChannelProvider = 'web_widget' | 'email' | 'slack' | 'whatsapp' | 'api' | 'discord' | 'telegram';

export interface Channel {
  id: string;
  name: string;
  provider: ChannelProvider;
  status: ChannelStatus;
  agentId: string;
  agentName: string;
  config: Record<string, unknown>;
  messageCount: number;
  lastMessageAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChannelCreateRequest {
  name: string;
  provider: ChannelProvider;
  agentId: string;
  config: Record<string, unknown>;
}

export interface ChannelUpdateRequest extends Partial<ChannelCreateRequest> {
  status?: ChannelStatus;
}

export interface ChannelTestResult {
  success: boolean;
  message: string;
  latencyMs: number;
}

export interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  content: string;
  variables: string[];
  category: string;
  currentVersionId: string;
  versions: PromptVersion[];
  createdAt: string;
  updatedAt: string;
}

export interface PromptVersion {
  id: string;
  promptId: string;
  version: number;
  content: string;
  changeNote: string;
  isPublished: boolean;
  createdBy: string;
  createdAt: string;
}

export interface PromptCreateRequest {
  name: string;
  description: string;
  content: string;
  category: string;
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resourceType: string;
  resourceId: string;
  details: Record<string, unknown>;
  ipAddress: string;
  timestamp: string;
}

export interface AuditLogFilters {
  userId?: string;
  action?: string;
  resourceType?: string;
  dateFrom?: string;
  dateTo?: string;
}
