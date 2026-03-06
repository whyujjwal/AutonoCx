import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Bot,
  MessageSquare,
  Clock,
  Star,
  MoreVertical,
  Pencil,
  Trash2,
  ToggleLeft,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { EmptyState } from '@/components/common/EmptyState';
import { formatNumber, formatDuration } from '@/lib/formatters';
import type { AgentStatus } from '@/types/agent.types';
import { clsx } from 'clsx';

const mockAgents = [
  {
    id: '1',
    name: 'Support Bot',
    description: 'General customer support agent handling billing, account, and product inquiries.',
    status: 'active' as AgentStatus,
    model: 'gpt-4o',
    provider: 'openai' as const,
    conversationCount: 4521,
    avgResolutionTime: 180000,
    satisfactionScore: 4.6,
    tools: ['lookup_account', 'process_refund', 'send_email'],
  },
  {
    id: '2',
    name: 'Auth Agent',
    description: 'Specialized agent for authentication and account security issues.',
    status: 'active' as AgentStatus,
    model: 'claude-3-5-sonnet',
    provider: 'anthropic' as const,
    conversationCount: 1234,
    avgResolutionTime: 120000,
    satisfactionScore: 4.8,
    tools: ['reset_password', 'verify_identity', 'send_2fa'],
  },
  {
    id: '3',
    name: 'Tech Support',
    description: 'Technical support for API integrations and developer-related questions.',
    status: 'active' as AgentStatus,
    model: 'gpt-4o',
    provider: 'openai' as const,
    conversationCount: 890,
    avgResolutionTime: 300000,
    satisfactionScore: 4.5,
    tools: ['search_docs', 'create_ticket', 'lookup_logs'],
  },
  {
    id: '4',
    name: 'Billing Agent',
    description: 'Handles billing, invoicing, and payment-related customer requests.',
    status: 'inactive' as AgentStatus,
    model: 'claude-3-5-haiku',
    provider: 'anthropic' as const,
    conversationCount: 2100,
    avgResolutionTime: 150000,
    satisfactionScore: 4.3,
    tools: ['lookup_invoice', 'process_refund', 'update_plan'],
  },
  {
    id: '5',
    name: 'Onboarding Assistant',
    description: 'Guides new customers through product setup and initial configuration.',
    status: 'draft' as AgentStatus,
    model: 'gemini-1.5-pro',
    provider: 'google' as const,
    conversationCount: 0,
    tools: ['create_workspace', 'send_guide', 'schedule_demo'],
  },
];

const statusBadgeVariant: Record<AgentStatus, 'success' | 'default' | 'warning'> = {
  active: 'success',
  inactive: 'default',
  draft: 'warning',
};

export default function AgentsPage() {
  const [_agents] = useState(mockAgents);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Agents</h1>
          <p className="mt-1 text-surface-500">Configure and manage your AI agents</p>
        </div>
        <Link to="/agents/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>Create Agent</Button>
        </Link>
      </div>

      {_agents.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-12 w-12" />}
          title="No agents configured"
          description="Create your first AI agent to start handling customer conversations."
          action={
            <Link to="/agents/new">
              <Button leftIcon={<Plus className="h-4 w-4" />}>Create Agent</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {_agents.map((agent) => (
            <Card key={agent.id} padding="none" hover>
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={clsx(
                        'flex h-10 w-10 items-center justify-center rounded-lg',
                        agent.status === 'active' ? 'bg-brand-50' : 'bg-surface-100',
                      )}
                    >
                      <Bot
                        className={clsx(
                          'h-5 w-5',
                          agent.status === 'active' ? 'text-brand-600' : 'text-surface-400',
                        )}
                      />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-surface-800">{agent.name}</h3>
                      <p className="text-xs text-surface-500">
                        {agent.model} &middot; {agent.provider}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={statusBadgeVariant[agent.status]} dot size="sm">
                      {agent.status}
                    </Badge>
                    <Dropdown
                      trigger={
                        <button className="rounded p-1 text-surface-400 hover:bg-surface-50">
                          <MoreVertical className="h-4 w-4" />
                        </button>
                      }
                      items={[
                        {
                          id: 'edit',
                          label: 'Edit',
                          icon: <Pencil className="h-4 w-4" />,
                          onClick: () => {},
                        },
                        {
                          id: 'toggle',
                          label: agent.status === 'active' ? 'Deactivate' : 'Activate',
                          icon: <ToggleLeft className="h-4 w-4" />,
                          onClick: () => {},
                        },
                        {
                          id: 'delete',
                          label: 'Delete',
                          icon: <Trash2 className="h-4 w-4" />,
                          onClick: () => {},
                          variant: 'danger',
                          divider: true,
                        },
                      ]}
                    />
                  </div>
                </div>
                <p className="mt-3 text-sm text-surface-600 line-clamp-2">{agent.description}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {agent.tools.slice(0, 3).map((tool) => (
                    <Badge key={tool} variant="outline" size="sm">
                      {tool}
                    </Badge>
                  ))}
                  {agent.tools.length > 3 && (
                    <Badge variant="outline" size="sm">
                      +{agent.tools.length - 3}
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-surface-100 px-5 py-3">
                <div className="flex items-center gap-1.5 text-xs text-surface-500">
                  <MessageSquare className="h-3.5 w-3.5" />
                  {formatNumber(agent.conversationCount)}
                </div>
                {agent.avgResolutionTime && (
                  <div className="flex items-center gap-1.5 text-xs text-surface-500">
                    <Clock className="h-3.5 w-3.5" />
                    {formatDuration(agent.avgResolutionTime)}
                  </div>
                )}
                {agent.satisfactionScore && (
                  <div className="flex items-center gap-1.5 text-xs text-surface-500">
                    <Star className="h-3.5 w-3.5 text-amber-400" />
                    {agent.satisfactionScore.toFixed(1)}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
