import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Check, X, Clock, AlertTriangle, Eye } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs } from '@/components/ui/Tabs';
import { Modal } from '@/components/ui/Modal';
import { formatRelativeTime } from '@/lib/formatters';
import type { RiskLevel } from '@/types/action.types';
import { clsx } from 'clsx';

const mockPendingActions = [
  {
    id: '1',
    conversationId: 'conv-123',
    agentName: 'Support Bot',
    type: 'process_refund',
    category: 'refund' as const,
    description: 'Refund $45.00 for order #ORD-9821 - customer reports duplicate charge',
    riskLevel: 'high' as RiskLevel,
    parameters: { orderId: 'ORD-9821', amount: 4500, reason: 'duplicate_charge' },
    createdAt: new Date(Date.now() - 120000).toISOString(),
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
  },
  {
    id: '2',
    conversationId: 'conv-456',
    agentName: 'Auth Agent',
    type: 'reset_password',
    category: 'account_change' as const,
    description: 'Reset password for user user@example.com - failed 2FA verification',
    riskLevel: 'high' as RiskLevel,
    parameters: { userId: 'usr-567', email: 'user@example.com' },
    createdAt: new Date(Date.now() - 300000).toISOString(),
    expiresAt: new Date(Date.now() + 1800000).toISOString(),
  },
  {
    id: '3',
    conversationId: 'conv-789',
    agentName: 'Billing Agent',
    type: 'update_plan',
    category: 'account_change' as const,
    description: 'Upgrade plan from Basic to Pro for customer Acme Corp',
    riskLevel: 'medium' as RiskLevel,
    parameters: { customerId: 'cust-890', fromPlan: 'basic', toPlan: 'pro' },
    createdAt: new Date(Date.now() - 600000).toISOString(),
    expiresAt: new Date(Date.now() + 7200000).toISOString(),
  },
  {
    id: '4',
    conversationId: 'conv-101',
    agentName: 'Support Bot',
    type: 'send_email',
    category: 'external_api' as const,
    description: 'Send custom promotional email to customer dave@acme.com',
    riskLevel: 'low' as RiskLevel,
    parameters: { to: 'dave@acme.com', subject: 'Your special offer', template: 'promo_v2' },
    createdAt: new Date(Date.now() - 900000).toISOString(),
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
  },
];

const riskColors: Record<RiskLevel, 'success' | 'warning' | 'danger' | 'default'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

const stats = {
  pending: 4,
  approvedToday: 23,
  rejectedToday: 3,
  avgApprovalTime: '2.4m',
};

export default function ActionQueuePage() {
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedAction, setSelectedAction] = useState<typeof mockPendingActions[number] | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const tabs = [
    { id: 'pending', label: 'Pending', count: stats.pending },
    { id: 'history', label: 'History' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Action Queue</h1>
          <p className="mt-1 text-surface-500">Review and approve actions requiring human oversight</p>
        </div>
        <Link to="/actions/history">
          <Button variant="outline">View Full History</Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Pending', value: stats.pending, icon: Clock, color: 'text-warning-500 bg-warning-50' },
          { label: 'Approved Today', value: stats.approvedToday, icon: Check, color: 'text-success-500 bg-success-50' },
          { label: 'Rejected Today', value: stats.rejectedToday, icon: X, color: 'text-danger-500 bg-danger-50' },
          { label: 'Avg Approval Time', value: stats.avgApprovalTime, icon: Clock, color: 'text-brand-500 bg-brand-50' },
        ].map((stat) => (
          <Card key={stat.label} padding="md">
            <div className="flex items-center gap-3">
              <div className={clsx('rounded-lg p-2', stat.color.split(' ')[1])}>
                <stat.icon className={clsx('h-4 w-4', stat.color.split(' ')[0])} />
              </div>
              <div>
                <p className="text-lg font-bold text-surface-900">{stat.value}</p>
                <p className="text-xs text-surface-500">{stat.label}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Pending Actions */}
      <div className="space-y-3">
        {mockPendingActions.map((action) => (
          <Card key={action.id} padding="none">
            <div className="flex items-center justify-between px-5 py-4">
              <div className="flex items-start gap-4 flex-1 min-w-0">
                <div className={clsx(
                  'flex h-10 w-10 items-center justify-center rounded-lg shrink-0',
                  action.riskLevel === 'high' ? 'bg-danger-50' : action.riskLevel === 'medium' ? 'bg-warning-50' : 'bg-surface-100',
                )}>
                  {action.riskLevel === 'high' ? (
                    <AlertTriangle className="h-5 w-5 text-danger-500" />
                  ) : (
                    <ShieldCheck className="h-5 w-5 text-surface-500" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-surface-800">{action.type}</span>
                    <Badge variant={riskColors[action.riskLevel]} size="sm">{action.riskLevel} risk</Badge>
                    <Badge variant="outline" size="sm">{action.category}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-surface-600">{action.description}</p>
                  <div className="mt-1.5 flex items-center gap-3 text-xs text-surface-500">
                    <span>Agent: {action.agentName}</span>
                    <span>&middot;</span>
                    <span>{formatRelativeTime(action.createdAt)}</span>
                    <span>&middot;</span>
                    <Link to={`/conversations/${action.conversationId}`} className="text-brand-600 hover:underline">
                      View conversation
                    </Link>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button variant="ghost" size="sm" leftIcon={<Eye className="h-3.5 w-3.5" />} onClick={() => setSelectedAction(action)}>
                  Review
                </Button>
                <Button variant="outline" size="sm" leftIcon={<X className="h-3.5 w-3.5" />} className="text-danger-500 hover:bg-danger-50">
                  Reject
                </Button>
                <Button size="sm" leftIcon={<Check className="h-3.5 w-3.5" />}>
                  Approve
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Review Modal */}
      <Modal isOpen={!!selectedAction} onClose={() => setSelectedAction(null)} title="Review Action" size="lg">
        {selectedAction && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-surface-500">Type:</span> <span className="font-medium ml-2">{selectedAction.type}</span></div>
              <div><span className="text-surface-500">Risk:</span> <Badge variant={riskColors[selectedAction.riskLevel]} size="sm" className="ml-2">{selectedAction.riskLevel}</Badge></div>
              <div><span className="text-surface-500">Agent:</span> <span className="font-medium ml-2">{selectedAction.agentName}</span></div>
              <div><span className="text-surface-500">Category:</span> <span className="font-medium ml-2">{selectedAction.category}</span></div>
            </div>
            <div>
              <p className="text-sm font-medium text-surface-700 mb-1">Description</p>
              <p className="text-sm text-surface-600">{selectedAction.description}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-surface-700 mb-1">Parameters</p>
              <pre className="rounded-lg bg-surface-50 p-3 text-xs font-mono overflow-auto">
                {JSON.stringify(selectedAction.parameters, null, 2)}
              </pre>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-surface-700">Rejection Reason (optional)</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={2}
                placeholder="Provide a reason if rejecting..."
                className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setSelectedAction(null)}>Cancel</Button>
              <Button variant="danger" leftIcon={<X className="h-4 w-4" />}>Reject</Button>
              <Button leftIcon={<Check className="h-4 w-4" />}>Approve</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
