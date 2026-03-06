export interface DashboardMetrics {
  totalConversations: number;
  activeConversations: number;
  resolutionRate: number;
  avgResponseTimeMs: number;
  avgResolutionTimeMs: number;
  csatScore: number;
  totalCost: number;
  conversationsToday: number;
  conversationsTrend: number;
  resolutionTrend: number;
  responseTimeTrend: number;
  csatTrend: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface ConversationMetrics {
  byStatus: Record<string, number>;
  byChannel: Record<string, number>;
  byAgent: { agentId: string; agentName: string; count: number }[];
  timeline: TimeSeriesPoint[];
  sentimentDistribution: Record<string, number>;
}

export interface CostBreakdown {
  totalCost: number;
  byModel: { model: string; cost: number; tokens: number }[];
  byAgent: { agentId: string; agentName: string; cost: number }[];
  timeline: TimeSeriesPoint[];
  avgCostPerConversation: number;
  avgCostPerMessage: number;
}

export interface AnalyticsFilters {
  dateFrom: string;
  dateTo: string;
  agentId?: string;
  channel?: string;
}
