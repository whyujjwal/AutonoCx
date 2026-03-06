/** Shared enumerations used across frontend and backend */

export const ConversationStatus = {
  ACTIVE: "active",
  WAITING_HUMAN: "waiting_human",
  ESCALATED: "escalated",
  RESOLVED: "resolved",
  CLOSED: "closed",
} as const;
export type ConversationStatus = (typeof ConversationStatus)[keyof typeof ConversationStatus];

export const Priority = {
  LOW: "low",
  NORMAL: "normal",
  HIGH: "high",
  URGENT: "urgent",
} as const;
export type Priority = (typeof Priority)[keyof typeof Priority];

export const Channel = {
  WEBCHAT: "webchat",
  WHATSAPP: "whatsapp",
  EMAIL: "email",
  VOICE: "voice",
  SMS: "sms",
} as const;
export type Channel = (typeof Channel)[keyof typeof Channel];

export const MessageRole = {
  CUSTOMER: "customer",
  ASSISTANT: "assistant",
  SYSTEM: "system",
  TOOL: "tool",
} as const;
export type MessageRole = (typeof MessageRole)[keyof typeof MessageRole];

export const ActionStatus = {
  PENDING: "pending",
  AWAITING_APPROVAL: "awaiting_approval",
  APPROVED: "approved",
  REJECTED: "rejected",
  EXECUTING: "executing",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;
export type ActionStatus = (typeof ActionStatus)[keyof typeof ActionStatus];

export const UserRole = {
  ADMIN: "admin",
  SUPERVISOR: "supervisor",
  AGENT_REVIEWER: "agent_reviewer",
  DEVELOPER: "developer",
  VIEWER: "viewer",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const RiskLevel = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
} as const;
export type RiskLevel = (typeof RiskLevel)[keyof typeof RiskLevel];

export const Sentiment = {
  POSITIVE: "positive",
  NEUTRAL: "neutral",
  NEGATIVE: "negative",
} as const;
export type Sentiment = (typeof Sentiment)[keyof typeof Sentiment];

export const DocumentStatus = {
  PENDING: "pending",
  PROCESSING: "processing",
  INDEXED: "indexed",
  FAILED: "failed",
} as const;
export type DocumentStatus = (typeof DocumentStatus)[keyof typeof DocumentStatus];

export const LLMProvider = {
  OPENAI: "openai",
  ANTHROPIC: "anthropic",
} as const;
export type LLMProvider = (typeof LLMProvider)[keyof typeof LLMProvider];

export const WorkflowTrigger = {
  INTENT: "intent",
  KEYWORD: "keyword",
  MANUAL: "manual",
  SCHEDULED: "scheduled",
} as const;
export type WorkflowTrigger = (typeof WorkflowTrigger)[keyof typeof WorkflowTrigger];

export const PromptCategory = {
  SYSTEM: "system",
  INTENT: "intent",
  TOOL: "tool",
  GUARD: "guard",
  GREETING: "greeting",
} as const;
export type PromptCategory = (typeof PromptCategory)[keyof typeof PromptCategory];
