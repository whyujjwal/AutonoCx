import { useState } from 'react';
import { ArrowLeft, Search, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Table, type Column } from '@/components/ui/Table';
import { formatDateTime } from '@/lib/formatters';
import type { ActionStatus, RiskLevel } from '@/types/action.types';

interface ActionHistoryItem {
  id: string;
  type: string;
  category: string;
  agentName: string;
  riskLevel: RiskLevel;
  status: ActionStatus;
  reviewedBy?: string;
  createdAt: string;
  reviewedAt?: string;
}

const mockHistory: ActionHistoryItem[] = [
  { id: '1', type: 'process_refund', category: 'refund', agentName: 'Support Bot', riskLevel: 'high', status: 'approved', reviewedBy: 'John Admin', createdAt: new Date(Date.now() - 3600000).toISOString(), reviewedAt: new Date(Date.now() - 3300000).toISOString() },
  { id: '2', type: 'send_email', category: 'external_api', agentName: 'General Agent', riskLevel: 'low', status: 'auto_approved', createdAt: new Date(Date.now() - 7200000).toISOString() },
  { id: '3', type: 'reset_password', category: 'account_change', agentName: 'Auth Agent', riskLevel: 'high', status: 'rejected', reviewedBy: 'Jane Admin', createdAt: new Date(Date.now() - 10800000).toISOString(), reviewedAt: new Date(Date.now() - 10500000).toISOString() },
  { id: '4', type: 'update_plan', category: 'account_change', agentName: 'Billing Agent', riskLevel: 'medium', status: 'approved', reviewedBy: 'John Admin', createdAt: new Date(Date.now() - 14400000).toISOString(), reviewedAt: new Date(Date.now() - 14200000).toISOString() },
  { id: '5', type: 'create_ticket', category: 'external_api', agentName: 'Support Bot', riskLevel: 'low', status: 'auto_approved', createdAt: new Date(Date.now() - 18000000).toISOString() },
  { id: '6', type: 'process_refund', category: 'refund', agentName: 'Billing Agent', riskLevel: 'high', status: 'expired', createdAt: new Date(Date.now() - 86400000).toISOString() },
];

const statusVariant: Record<ActionStatus, 'success' | 'danger' | 'default' | 'info' | 'warning'> = {
  approved: 'success',
  rejected: 'danger',
  expired: 'default',
  auto_approved: 'info',
  pending: 'warning',
};

const riskVariant: Record<RiskLevel, 'success' | 'warning' | 'danger' | 'default'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

export default function ActionHistoryPage() {
  const navigate = useNavigate();
  const [_search, setSearch] = useState('');

  const columns: Column<ActionHistoryItem>[] = [
    {
      key: 'type',
      header: 'Action',
      sortable: true,
      render: (item) => (
        <div>
          <p className="font-medium text-surface-800">{item.type}</p>
          <p className="text-xs text-surface-500">{item.category}</p>
        </div>
      ),
    },
    { key: 'agentName', header: 'Agent', sortable: true },
    {
      key: 'riskLevel',
      header: 'Risk',
      render: (item) => <Badge variant={riskVariant[item.riskLevel]} size="sm">{item.riskLevel}</Badge>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <Badge variant={statusVariant[item.status]} dot size="sm">{item.status.replace('_', ' ')}</Badge>,
    },
    {
      key: 'reviewedBy',
      header: 'Reviewed By',
      render: (item) => <span className="text-surface-600">{item.reviewedBy ?? '-'}</span>,
    },
    {
      key: 'createdAt',
      header: 'Created',
      sortable: true,
      render: (item) => <span className="text-surface-500">{formatDateTime(item.createdAt)}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/actions')} className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Action History</h1>
            <p className="mt-1 text-surface-500">Complete history of all action executions</p>
          </div>
        </div>
        <Button variant="outline" leftIcon={<Download className="h-4 w-4" />}>Export CSV</Button>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
          <input
            type="text"
            placeholder="Search actions..."
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-surface-200 bg-white py-2 pl-10 pr-4 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        <Select options={[{ value: '', label: 'All statuses' }, { value: 'approved', label: 'Approved' }, { value: 'rejected', label: 'Rejected' }, { value: 'expired', label: 'Expired' }, { value: 'auto_approved', label: 'Auto Approved' }]} />
        <Select options={[{ value: '', label: 'All risk levels' }, { value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }]} />
      </div>

      <Table columns={columns} data={mockHistory} keyExtractor={(a) => a.id} page={1} totalPages={5} onPageChange={() => {}} />
    </div>
  );
}
