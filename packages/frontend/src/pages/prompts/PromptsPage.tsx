import { Link } from 'react-router-dom';
import { Plus, FileText, MoreVertical, Pencil, Trash2, Copy } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { formatDate, truncate } from '@/lib/formatters';

const mockPrompts = [
  {
    id: '1',
    name: 'Customer Support System Prompt',
    description: 'Main system prompt for customer support agents',
    category: 'system',
    content: 'You are a helpful customer support agent for AutonoCX. Be polite, professional, and solution-oriented...',
    currentVersion: 5,
    updatedAt: '2024-03-01T10:00:00Z',
    variables: ['company_name', 'agent_name', 'tone'],
  },
  {
    id: '2',
    name: 'Refund Decision Template',
    description: 'Template for evaluating refund eligibility',
    category: 'decision',
    content: 'Evaluate the following refund request based on our policy guidelines...',
    currentVersion: 3,
    updatedAt: '2024-02-28T14:00:00Z',
    variables: ['order_id', 'amount', 'reason'],
  },
  {
    id: '3',
    name: 'Escalation Summary',
    description: 'Generates a summary when escalating to a human agent',
    category: 'template',
    content: 'Summarize the conversation so far including the key issue, sentiment, and recommended actions...',
    currentVersion: 2,
    updatedAt: '2024-02-25T09:00:00Z',
    variables: ['conversation_id', 'priority'],
  },
  {
    id: '4',
    name: 'Knowledge Base Query',
    description: 'Prompt for searching and synthesizing knowledge base results',
    category: 'rag',
    content: 'Given the following context from our knowledge base, answer the user question accurately...',
    currentVersion: 4,
    updatedAt: '2024-02-20T16:00:00Z',
    variables: ['context', 'query'],
  },
];

const categoryColors: Record<string, 'info' | 'success' | 'warning' | 'default'> = {
  system: 'info',
  decision: 'warning',
  template: 'success',
  rag: 'default',
};

export default function PromptsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Prompt Templates</h1>
          <p className="mt-1 text-surface-500">Manage and version your prompt templates</p>
        </div>
        <Link to="/prompts/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>Create Prompt</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {mockPrompts.map((prompt) => (
          <Card key={prompt.id} padding="none" hover>
            <div className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-100">
                    <FileText className="h-4.5 w-4.5 text-surface-500" />
                  </div>
                  <div>
                    <Link to={`/prompts/${prompt.id}`} className="text-sm font-semibold text-surface-800 hover:text-brand-600">
                      {prompt.name}
                    </Link>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge variant={categoryColors[prompt.category] ?? 'default'} size="sm">
                        {prompt.category}
                      </Badge>
                      <span className="text-xs text-surface-400">v{prompt.currentVersion}</span>
                    </div>
                  </div>
                </div>
                <Dropdown
                  trigger={
                    <button className="rounded p-1 text-surface-400 hover:bg-surface-50">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  }
                  items={[
                    { id: 'edit', label: 'Edit', icon: <Pencil className="h-4 w-4" />, onClick: () => {} },
                    { id: 'duplicate', label: 'Duplicate', icon: <Copy className="h-4 w-4" />, onClick: () => {} },
                    { id: 'delete', label: 'Delete', icon: <Trash2 className="h-4 w-4" />, onClick: () => {}, variant: 'danger', divider: true },
                  ]}
                />
              </div>
              <p className="mt-2 text-sm text-surface-500">{prompt.description}</p>
              <div className="mt-3 rounded-lg bg-surface-50 p-3">
                <p className="text-xs font-mono text-surface-600">
                  {truncate(prompt.content, 120)}
                </p>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div className="flex gap-1">
                  {prompt.variables.map((v) => (
                    <Badge key={v} variant="outline" size="sm">
                      {`{{${v}}}`}
                    </Badge>
                  ))}
                </div>
                <span className="text-xs text-surface-400">{formatDate(prompt.updatedAt)}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
