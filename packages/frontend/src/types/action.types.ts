export type ActionStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'auto_approved';
export type ActionCategory = 'refund' | 'account_change' | 'escalation' | 'data_access' | 'external_api' | 'custom';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Action {
  id: string;
  conversationId: string;
  agentId: string;
  agentName: string;
  type: string;
  category: ActionCategory;
  description: string;
  parameters: Record<string, unknown>;
  riskLevel: RiskLevel;
  status: ActionStatus;
  reviewedBy?: string;
  reviewedAt?: string;
  reviewNote?: string;
  createdAt: string;
  expiresAt: string;
}

export interface ActionApproveRequest {
  note?: string;
}

export interface ActionRejectRequest {
  reason: string;
}

export interface ActionStats {
  totalPending: number;
  totalApproved: number;
  totalRejected: number;
  avgApprovalTimeMs: number;
  byCategory: Record<ActionCategory, number>;
  byRiskLevel: Record<RiskLevel, number>;
}
