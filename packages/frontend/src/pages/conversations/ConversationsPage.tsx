import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Plus, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { EmptyState } from '@/components/common/EmptyState';
import { formatRelativeTime, truncate } from '@/lib/formatters';
import { clsx } from 'clsx';
import type { ConversationStatus, ChannelType } from '@/types/conversation.types';

// Mock data
const mockConversations = [
  {
    id: '1',
    title: 'Billing inquiry about monthly subscription charges',
    status: 'active' as ConversationStatus,
    channel: 'web' as ChannelType,
    agentName: 'Support Bot',
    customerName: 'Alice Johnson',
    customerEmail: 'alice@example.com',
    messageCount: 8,
    lastMessageAt: new Date(Date.now() - 120000).toISOString(),
    sentiment: 'neutral' as const,
    tags: ['billing', 'subscription'],
  },
  {
    id: '2',
    title: 'Cannot access my account after password change',
    status: 'escalated' as ConversationStatus,
    channel: 'email' as ChannelType,
    agentName: 'Auth Agent',
    customerName: 'Bob Smith',
    customerEmail: 'bob@example.com',
    messageCount: 12,
    lastMessageAt: new Date(Date.now() - 300000).toISOString(),
    sentiment: 'negative' as const,
    tags: ['account', 'auth'],
  },
  {
    id: '3',
    title: 'How to integrate your API with our CRM system',
    status: 'active' as ConversationStatus,
    channel: 'slack' as ChannelType,
    agentName: 'Tech Support',
    customerName: 'Carol Davis',
    customerEmail: 'carol@example.com',
    messageCount: 5,
    lastMessageAt: new Date(Date.now() - 600000).toISOString(),
    sentiment: 'positive' as const,
    tags: ['integration', 'api'],
  },
  {
    id: '4',
    title: 'Request refund for accidental purchase',
    status: 'waiting' as ConversationStatus,
    channel: 'whatsapp' as ChannelType,
    agentName: 'Billing Agent',
    customerName: 'David Lee',
    customerEmail: 'david@example.com',
    messageCount: 3,
    lastMessageAt: new Date(Date.now() - 1800000).toISOString(),
    sentiment: 'negative' as const,
    tags: ['refund', 'billing'],
  },
  {
    id: '5',
    title: 'Thank you for resolving my issue quickly',
    status: 'resolved' as ConversationStatus,
    channel: 'web' as ChannelType,
    agentName: 'General Agent',
    customerName: 'Eve Wilson',
    customerEmail: 'eve@example.com',
    messageCount: 6,
    lastMessageAt: new Date(Date.now() - 3600000).toISOString(),
    sentiment: 'positive' as const,
    tags: ['feedback'],
  },
];

const statusColors: Record<ConversationStatus, 'success' | 'info' | 'warning' | 'danger' | 'default'> = {
  active: 'info',
  waiting: 'warning',
  escalated: 'danger',
  resolved: 'success',
  closed: 'default',
};

const sentimentIcons: Record<string, string> = {
  positive: 'text-success-500',
  neutral: 'text-surface-400',
  negative: 'text-danger-500',
};

const tabs = [
  { id: 'all', label: 'All', count: 156 },
  { id: 'active', label: 'Active', count: 42 },
  { id: 'escalated', label: 'Escalated', count: 8 },
  { id: 'waiting', label: 'Waiting', count: 15 },
  { id: 'resolved', label: 'Resolved', count: 91 },
];

export default function ConversationsPage() {
  const [activeTab, setActiveTab] = useState('all');
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const filteredConversations = mockConversations.filter((conv) => {
    if (activeTab !== 'all' && conv.status !== activeTab) return false;
    if (search && !conv.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Conversations</h1>
          <p className="mt-1 text-surface-500">Monitor and manage customer conversations</p>
        </div>
        <Button leftIcon={<Plus className="h-4 w-4" />}>New Conversation</Button>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-surface-200 bg-white py-2 pl-10 pr-4 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        <Button
          variant="outline"
          leftIcon={<Filter className="h-4 w-4" />}
          onClick={() => setShowFilters(!showFilters)}
        >
          Filters
        </Button>
      </div>

      {showFilters && (
        <Card padding="md" className="animate-slide-up">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Select
              label="Channel"
              options={[
                { value: '', label: 'All channels' },
                { value: 'web', label: 'Web' },
                { value: 'email', label: 'Email' },
                { value: 'slack', label: 'Slack' },
                { value: 'whatsapp', label: 'WhatsApp' },
              ]}
            />
            <Select
              label="Agent"
              options={[
                { value: '', label: 'All agents' },
                { value: 'support-bot', label: 'Support Bot' },
                { value: 'auth-agent', label: 'Auth Agent' },
                { value: 'tech-support', label: 'Tech Support' },
              ]}
            />
            <Select
              label="Sentiment"
              options={[
                { value: '', label: 'All' },
                { value: 'positive', label: 'Positive' },
                { value: 'neutral', label: 'Neutral' },
                { value: 'negative', label: 'Negative' },
              ]}
            />
          </div>
        </Card>
      )}

      {filteredConversations.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-12 w-12" />}
          title="No conversations found"
          description="Try adjusting your filters or search query."
        />
      ) : (
        <div className="space-y-2">
          {filteredConversations.map((conv) => (
            <Link key={conv.id} to={`/conversations/${conv.id}`}>
              <Card hover padding="none" className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          'h-2 w-2 rounded-full shrink-0',
                          sentimentIcons[conv.sentiment ?? 'neutral']?.replace('text-', 'bg-'),
                        )}
                      />
                      <h3 className="text-sm font-medium text-surface-800 truncate">
                        {conv.title}
                      </h3>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-surface-500">
                      <span>{conv.customerName}</span>
                      <span>&middot;</span>
                      <span>{conv.agentName}</span>
                      <span>&middot;</span>
                      <span>{conv.channel}</span>
                      <span>&middot;</span>
                      <span>{conv.messageCount} messages</span>
                    </div>
                    <div className="mt-2 flex gap-1.5">
                      {conv.tags.map((tag) => (
                        <Badge key={tag} variant="outline" size="sm">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <Badge variant={statusColors[conv.status]} dot>
                      {conv.status}
                    </Badge>
                    <span className="text-xs text-surface-400">
                      {formatRelativeTime(conv.lastMessageAt)}
                    </span>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
