import {
  MessageSquare,
  CheckCircle,
  Clock,
  Star,
  TrendingUp,
  TrendingDown,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatNumber, formatPercentage, formatDuration } from '@/lib/formatters';
import { clsx } from 'clsx';

// Mock data for dashboard
const kpiData = [
  {
    label: 'Total Conversations',
    value: 12847,
    trend: 12.5,
    icon: MessageSquare,
    color: 'text-brand-600',
    bgColor: 'bg-brand-50',
  },
  {
    label: 'Resolution Rate',
    value: 94.2,
    trend: 3.1,
    icon: CheckCircle,
    color: 'text-success-500',
    bgColor: 'bg-success-50',
    isPercent: true,
  },
  {
    label: 'Avg Response Time',
    value: 1200,
    trend: -8.4,
    icon: Clock,
    color: 'text-warning-500',
    bgColor: 'bg-warning-50',
    isDuration: true,
  },
  {
    label: 'CSAT Score',
    value: 4.7,
    trend: 2.0,
    icon: Star,
    color: 'text-amber-500',
    bgColor: 'bg-amber-50',
    suffix: '/5',
  },
];

const conversationTimeline = [
  { date: 'Mon', conversations: 180, resolved: 168 },
  { date: 'Tue', conversations: 210, resolved: 195 },
  { date: 'Wed', conversations: 195, resolved: 184 },
  { date: 'Thu', conversations: 230, resolved: 218 },
  { date: 'Fri', conversations: 255, resolved: 240 },
  { date: 'Sat', conversations: 120, resolved: 115 },
  { date: 'Sun', conversations: 95, resolved: 92 },
];

const channelDistribution = [
  { channel: 'Web', count: 4521 },
  { channel: 'Email', count: 3210 },
  { channel: 'Slack', count: 2890 },
  { channel: 'WhatsApp', count: 1420 },
  { channel: 'API', count: 806 },
];

const recentConversations = [
  { id: '1', title: 'Billing inquiry about subscription', status: 'active' as const, agent: 'Support Bot', time: '2m ago' },
  { id: '2', title: 'Password reset assistance', status: 'resolved' as const, agent: 'Auth Agent', time: '5m ago' },
  { id: '3', title: 'Feature request for reporting', status: 'escalated' as const, agent: 'General Agent', time: '12m ago' },
  { id: '4', title: 'Integration setup help', status: 'active' as const, agent: 'Tech Support', time: '18m ago' },
  { id: '5', title: 'Refund request processing', status: 'waiting' as const, agent: 'Billing Agent', time: '25m ago' },
];

const statusColors: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
  active: 'info',
  resolved: 'success',
  escalated: 'danger',
  waiting: 'warning',
};

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Dashboard</h1>
        <p className="mt-1 text-surface-500">Overview of your customer experience operations</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpiData.map((kpi) => (
          <Card key={kpi.label} padding="md">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-surface-500">{kpi.label}</p>
                <p className="mt-2 text-2xl font-bold text-surface-900">
                  {kpi.isPercent
                    ? formatPercentage(kpi.value)
                    : kpi.isDuration
                      ? formatDuration(kpi.value)
                      : formatNumber(kpi.value)}
                  {kpi.suffix ?? ''}
                </p>
              </div>
              <div className={clsx('rounded-lg p-2.5', kpi.bgColor)}>
                <kpi.icon className={clsx('h-5 w-5', kpi.color)} />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-1 text-sm">
              {kpi.trend > 0 ? (
                <TrendingUp className="h-4 w-4 text-success-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-danger-500" />
              )}
              <span className={kpi.trend > 0 ? 'text-success-500' : 'text-danger-500'}>
                {Math.abs(kpi.trend)}%
              </span>
              <span className="text-surface-400">vs last week</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card padding="md" className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Conversation Volume</CardTitle>
          </CardHeader>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={conversationTimeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="conversations"
                  stroke="#3366ff"
                  fill="#3366ff"
                  fillOpacity={0.1}
                  strokeWidth={2}
                  name="Total"
                />
                <Area
                  type="monotone"
                  dataKey="resolved"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.1}
                  strokeWidth={2}
                  name="Resolved"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card padding="md">
          <CardHeader>
            <CardTitle>By Channel</CardTitle>
          </CardHeader>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelDistribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis
                  type="category"
                  dataKey="channel"
                  stroke="#94a3b8"
                  fontSize={12}
                  width={70}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#3366ff" radius={[0, 4, 4, 0]} name="Conversations" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Recent Conversations */}
      <Card padding="none">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-200">
          <h3 className="text-lg font-semibold text-surface-900">Recent Conversations</h3>
          <Link
            to="/conversations"
            className="flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            View all <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="divide-y divide-surface-100">
          {recentConversations.map((conv) => (
            <Link
              key={conv.id}
              to={`/conversations/${conv.id}`}
              className="flex items-center justify-between px-6 py-3.5 hover:bg-surface-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-surface-800 truncate">{conv.title}</p>
                <p className="mt-0.5 text-xs text-surface-500">
                  {conv.agent} &middot; {conv.time}
                </p>
              </div>
              <Badge variant={statusColors[conv.status]} dot>
                {conv.status}
              </Badge>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
