export type WorkflowStatus = 'active' | 'inactive' | 'draft';
export type StepType = 'condition' | 'action' | 'llm_call' | 'tool_call' | 'human_review' | 'delay' | 'branch';

export interface WorkflowStep {
  id: string;
  type: StepType;
  name: string;
  config: Record<string, unknown>;
  nextSteps: string[];
  position: { x: number; y: number };
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  steps: WorkflowStep[];
  executionCount: number;
  avgExecutionTimeMs: number;
  lastExecutedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowCreateRequest {
  name: string;
  description: string;
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  steps: Omit<WorkflowStep, 'id'>[];
}

export interface WorkflowUpdateRequest extends Partial<WorkflowCreateRequest> {
  status?: WorkflowStatus;
}
