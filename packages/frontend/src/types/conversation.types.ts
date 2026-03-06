export type ConversationStatus = 'active' | 'waiting' | 'escalated' | 'resolved' | 'closed';
export type MessageRole = 'user' | 'assistant' | 'system';
export type ChannelType = 'web' | 'email' | 'slack' | 'whatsapp' | 'api';
export type SentimentScore = 'positive' | 'neutral' | 'negative';

export interface Message {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  metadata?: Record<string, unknown>;
  toolCalls?: ToolCall[];
  createdAt: string;
}

export interface ToolCall {
  id: string;
  toolName: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: 'pending' | 'completed' | 'failed';
}

export interface Conversation {
  id: string;
  title: string;
  status: ConversationStatus;
  channel: ChannelType;
  agentId: string;
  agentName: string;
  customerId?: string;
  customerName?: string;
  customerEmail?: string;
  sentiment?: SentimentScore;
  messageCount: number;
  lastMessageAt: string;
  createdAt: string;
  resolvedAt?: string;
  tags: string[];
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ConversationFilters {
  status?: ConversationStatus;
  channel?: ChannelType;
  agentId?: string;
  sentiment?: SentimentScore;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}
