import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email address'),
    organizationName: z.string().min(2, 'Organization name is required'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const agentSchema = z.object({
  name: z.string().min(1, 'Agent name is required'),
  description: z.string().min(1, 'Description is required'),
  model: z.string().min(1, 'Model is required'),
  provider: z.enum(['openai', 'anthropic', 'google']),
  systemPrompt: z.string().min(10, 'System prompt must be at least 10 characters'),
  temperature: z.number().min(0).max(2),
  maxTokens: z.number().min(1).max(128000),
  tools: z.array(z.string()),
  knowledgeBases: z.array(z.string()),
});

export const knowledgeBaseSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().min(1, 'Description is required'),
  embeddingModel: z.string().optional(),
});

export const workflowSchema = z.object({
  name: z.string().min(1, 'Workflow name is required'),
  description: z.string().min(1, 'Description is required'),
  triggerType: z.string().min(1, 'Trigger type is required'),
});

export const toolSchema = z.object({
  name: z.string().min(1, 'Tool name is required'),
  description: z.string().min(1, 'Description is required'),
  type: z.string().min(1, 'Type is required'),
  endpoint: z.string().url('Must be a valid URL').optional().or(z.literal('')),
});

export const promptSchema = z.object({
  name: z.string().min(1, 'Prompt name is required'),
  description: z.string().min(1, 'Description is required'),
  content: z.string().min(10, 'Prompt content must be at least 10 characters'),
  category: z.string().min(1, 'Category is required'),
});

export const channelSchema = z.object({
  name: z.string().min(1, 'Channel name is required'),
  provider: z.enum(['web_widget', 'email', 'slack', 'whatsapp', 'api', 'discord', 'telegram']),
  agentId: z.string().min(1, 'Agent is required'),
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type AgentFormData = z.infer<typeof agentSchema>;
export type KnowledgeBaseFormData = z.infer<typeof knowledgeBaseSchema>;
export type WorkflowFormData = z.infer<typeof workflowSchema>;
export type ToolFormData = z.infer<typeof toolSchema>;
export type PromptFormData = z.infer<typeof promptSchema>;
export type ChannelFormData = z.infer<typeof channelSchema>;
