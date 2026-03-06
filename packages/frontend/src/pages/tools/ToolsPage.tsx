import { Link } from 'react-router-dom';
import { Plus, Wrench, Code, Globe, Webhook, MoreVertical, Pencil, Trash2, Play } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, type Column } from '@/components/ui/Table';
import { Dropdown } from '@/components/ui/Dropdown';
import { formatNumber, formatRelativeTime } from '@/lib/formatters';

interface ToolItem {
  id: string;
  name: string;
  description: string;
  type: 'api' | 'function' | 'webhook';
  requiresApproval: boolean;
  riskLevel: 'low' | 'medium' | 'high';
  usageCount: number;
  lastUsedAt?: string;
}

const mockTools: ToolItem[] = [
  { id: '1', name: 'lookup_account', description: 'Look up customer account details by email or ID', type: 'api', requiresApproval: false, riskLevel: 'low', usageCount: 8923, lastUsedAt: new Date(Date.now() - 60000).toISOString() },
  { id: '2', name: 'process_refund', description: 'Process a refund for a customer order', type: 'api', requiresApproval: true, riskLevel: 'high', usageCount: 1456, lastUsedAt: new Date(Date.now() - 300000).toISOString() },
  { id: '3', name: 'send_email', description: 'Send an email to a customer', type: 'function', requiresApproval: false, riskLevel: 'medium', usageCount: 5678, lastUsedAt: new Date(Date.now() - 120000).toISOString() },
  { id: '4', name: 'search_docs', description: 'Search product documentation and knowledge base', type: 'function', requiresApproval: false, riskLevel: 'low', usageCount: 12345, lastUsedAt: new Date(Date.now() - 30000).toISOString() },
  { id: '5', name: 'create_ticket', description: 'Create a support ticket in the ticketing system', type: 'webhook', requiresApproval: false, riskLevel: 'low', usageCount: 3456, lastUsedAt: new Date(Date.now() - 900000).toISOString() },
  { id: '6', name: 'reset_password', description: 'Trigger a password reset for a user account', type: 'api', requiresApproval: true, riskLevel: 'high', usageCount: 890, lastUsedAt: new Date(Date.now() - 1800000).toISOString() },
  { id: '7', name: 'update_plan', description: 'Change the subscription plan for a customer', type: 'api', requiresApproval: true, riskLevel: 'high', usageCount: 234, lastUsedAt: new Date(Date.now() - 7200000).toISOString() },
];

const typeIcons: Record<string, typeof Code> = {
  api: Globe,
  function: Code,
  webhook: Webhook,
};

const riskColors: Record<string, 'success' | 'warning' | 'danger'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
};

export default function ToolsPage() {
  const columns: Column<ToolItem>[] = [
    {
      key: 'name',
      header: 'Tool',
      sortable: true,
      render: (tool) => {
        const Icon = typeIcons[tool.type] ?? Wrench;
        return (
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-100">
              <Icon className="h-4 w-4 text-surface-600" />
            </div>
            <div>
              <Link to={`/tools/${tool.id}`} className="font-medium text-surface-800 hover:text-brand-600">
                {tool.name}
              </Link>
              <p className="text-xs text-surface-500">{tool.description}</p>
            </div>
          </div>
        );
      },
    },
    {
      key: 'type',
      header: 'Type',
      render: (tool) => <Badge variant="outline" size="sm">{tool.type}</Badge>,
    },
    {
      key: 'riskLevel',
      header: 'Risk',
      render: (tool) => (
        <Badge variant={riskColors[tool.riskLevel]} size="sm">
          {tool.riskLevel}
        </Badge>
      ),
    },
    {
      key: 'requiresApproval',
      header: 'Approval',
      render: (tool) => (
        <span className={tool.requiresApproval ? 'text-warning-500 text-sm' : 'text-surface-400 text-sm'}>
          {tool.requiresApproval ? 'Required' : 'Auto'}
        </span>
      ),
    },
    {
      key: 'usageCount',
      header: 'Usage',
      sortable: true,
      render: (tool) => <span className="text-sm text-surface-700">{formatNumber(tool.usageCount)}</span>,
    },
    {
      key: 'lastUsedAt',
      header: 'Last Used',
      render: (tool) => (
        <span className="text-sm text-surface-500">
          {tool.lastUsedAt ? formatRelativeTime(tool.lastUsedAt) : 'Never'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-10',
      render: (tool) => (
        <Dropdown
          trigger={
            <button className="rounded p-1 text-surface-400 hover:bg-surface-50">
              <MoreVertical className="h-4 w-4" />
            </button>
          }
          items={[
            { id: 'edit', label: 'Edit', icon: <Pencil className="h-4 w-4" />, onClick: () => {} },
            { id: 'test', label: 'Test', icon: <Play className="h-4 w-4" />, onClick: () => {} },
            { id: 'delete', label: 'Delete', icon: <Trash2 className="h-4 w-4" />, onClick: () => {}, variant: 'danger', divider: true },
          ]}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Tools</h1>
          <p className="mt-1 text-surface-500">Manage tools that agents can use during conversations</p>
        </div>
        <Link to="/tools/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>Add Tool</Button>
        </Link>
      </div>

      <Table columns={columns} data={mockTools} keyExtractor={(t) => t.id} />
    </div>
  );
}
