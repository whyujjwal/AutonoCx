import { Link } from 'react-router-dom';
import { Plus, GitBranch, Play, Pause, Clock, MoreVertical, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Dropdown } from '@/components/ui/Dropdown';
import { formatNumber, formatDuration, formatRelativeTime } from '@/lib/formatters';
import type { WorkflowStatus } from '@/types/workflow.types';

const mockWorkflows = [
  {
    id: '1',
    name: 'Refund Processing',
    description: 'Automates refund requests with approval workflow based on amount thresholds.',
    status: 'active' as WorkflowStatus,
    triggerType: 'action_request',
    stepCount: 6,
    executionCount: 1234,
    avgExecutionTimeMs: 45000,
    lastExecutedAt: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: '2',
    name: 'Escalation Handler',
    description: 'Routes escalated conversations to appropriate teams based on issue category.',
    status: 'active' as WorkflowStatus,
    triggerType: 'conversation_escalated',
    stepCount: 4,
    executionCount: 456,
    avgExecutionTimeMs: 12000,
    lastExecutedAt: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: '3',
    name: 'New Customer Onboarding',
    description: 'Sends welcome emails and sets up initial resources for new customers.',
    status: 'inactive' as WorkflowStatus,
    triggerType: 'customer_created',
    stepCount: 8,
    executionCount: 89,
    avgExecutionTimeMs: 60000,
    lastExecutedAt: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: '4',
    name: 'CSAT Survey',
    description: 'Sends satisfaction survey after conversation is resolved.',
    status: 'draft' as WorkflowStatus,
    triggerType: 'conversation_resolved',
    stepCount: 3,
    executionCount: 0,
    avgExecutionTimeMs: 0,
  },
];

const statusVariant: Record<WorkflowStatus, 'success' | 'default' | 'warning'> = {
  active: 'success',
  inactive: 'default',
  draft: 'warning',
};

export default function WorkflowsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Workflows</h1>
          <p className="mt-1 text-surface-500">Automate processes with configurable workflows</p>
        </div>
        <Link to="/workflows/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>Create Workflow</Button>
        </Link>
      </div>

      <div className="space-y-3">
        {mockWorkflows.map((wf) => (
          <Card key={wf.id} padding="none">
            <div className="flex items-center justify-between px-5 py-4">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 shrink-0">
                  <GitBranch className="h-5 w-5 text-brand-600" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/workflows/${wf.id}`}
                      className="text-sm font-semibold text-surface-800 hover:text-brand-600"
                    >
                      {wf.name}
                    </Link>
                    <Badge variant={statusVariant[wf.status]} dot size="sm">
                      {wf.status}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-surface-500 truncate">{wf.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-6 shrink-0">
                <div className="hidden md:flex items-center gap-6 text-xs text-surface-500">
                  <div className="flex items-center gap-1.5">
                    <Play className="h-3.5 w-3.5" />
                    {formatNumber(wf.executionCount)} runs
                  </div>
                  {wf.avgExecutionTimeMs > 0 && (
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      {formatDuration(wf.avgExecutionTimeMs)} avg
                    </div>
                  )}
                  {wf.lastExecutedAt && (
                    <span>Last: {formatRelativeTime(wf.lastExecutedAt)}</span>
                  )}
                </div>
                <Badge variant="outline" size="sm">
                  {wf.stepCount} steps
                </Badge>
                <Dropdown
                  trigger={
                    <button className="rounded p-1.5 text-surface-400 hover:bg-surface-50">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  }
                  items={[
                    { id: 'edit', label: 'Edit', icon: <Pencil className="h-4 w-4" />, onClick: () => {} },
                    {
                      id: 'toggle',
                      label: wf.status === 'active' ? 'Pause' : 'Activate',
                      icon: wf.status === 'active' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />,
                      onClick: () => {},
                    },
                    { id: 'delete', label: 'Delete', icon: <Trash2 className="h-4 w-4" />, onClick: () => {}, variant: 'danger', divider: true },
                  ]}
                />
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
