/** WebSocket event types for real-time communication */

export type WSEventType =
  | "message.send"
  | "message.received"
  | "message.streaming"
  | "typing.start"
  | "typing.stop"
  | "action.pending"
  | "action.completed"
  | "action.failed"
  | "action.approval_required"
  | "conversation.escalated"
  | "conversation.resolved"
  | "conversation.assigned"
  | "error";

export interface WSEvent<T = unknown> {
  type: WSEventType;
  conversation_id: string;
  timestamp: string;
  data: T;
}

export interface MessageSendEvent {
  content: string;
  content_type: "text" | "image" | "audio" | "file";
  metadata?: Record<string, unknown>;
}

export interface MessageReceivedEvent {
  message_id: string;
  role: "assistant" | "system";
  content: string;
  content_type: string;
  tool_calls?: ToolCallEvent[];
}

export interface MessageStreamingEvent {
  message_id: string;
  delta: string;
  done: boolean;
}

export interface ToolCallEvent {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "executing" | "completed" | "failed";
  result?: Record<string, unknown>;
}

export interface ActionApprovalEvent {
  action_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  risk_score: number;
  risk_factors: string[];
}

export interface ConversationEscalatedEvent {
  reason: string;
  assigned_to?: string;
}

export interface WSErrorEvent {
  code: string;
  message: string;
}
