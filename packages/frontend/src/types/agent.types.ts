export type AgentStatus = 'active' | 'inactive' | 'draft';
export type ModelProvider = 'openai' | 'anthropic' | 'google';

export interface Agent {
  id: string;
  name: string;
  description: string;
  status: AgentStatus;
  model: string;
  provider: ModelProvider;
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  tools: string[];
  knowledgeBases: string[];
  conversationCount: number;
  avgResolutionTime?: number;
  satisfactionScore?: number;
  createdAt: string;
  updatedAt: string;
}

export interface AgentCreateRequest {
  name: string;
  description: string;
  model: string;
  provider: ModelProvider;
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  tools: string[];
  knowledgeBases: string[];
}

export interface AgentUpdateRequest extends Partial<AgentCreateRequest> {
  status?: AgentStatus;
}

export interface AgentTestRequest {
  message: string;
}

export interface AgentTestResponse {
  response: string;
  tokensUsed: number;
  latencyMs: number;
  toolCalls: string[];
}
