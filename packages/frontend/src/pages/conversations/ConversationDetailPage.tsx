import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Send,
  Phone,
  AlertTriangle,
  CheckCircle,
  User,
  Bot,
  Clock,
  Tag,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Avatar } from '@/components/ui/Avatar';
import { formatRelativeTime } from '@/lib/formatters';
import { clsx } from 'clsx';

// Mock messages
const mockMessages = [
  {
    id: '1',
    role: 'user' as const,
    content: 'Hi, I have a question about my monthly subscription charge. It seems higher than expected.',
    createdAt: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: '2',
    role: 'assistant' as const,
    content:
      'Hello! I\'d be happy to help you with your billing inquiry. Let me look into your account details. I can see your subscription was recently upgraded from the Basic plan to the Pro plan, which may explain the difference in charges.',
    createdAt: new Date(Date.now() - 540000).toISOString(),
    toolCalls: [
      { id: 't1', toolName: 'lookup_account', status: 'completed' as const, arguments: {} },
    ],
  },
  {
    id: '3',
    role: 'user' as const,
    content: 'I didn\'t authorize any upgrade. Can you please check when this change was made?',
    createdAt: new Date(Date.now() - 480000).toISOString(),
  },
  {
    id: '4',
    role: 'assistant' as const,
    content:
      'I understand your concern. Looking at the account activity log, the upgrade was made on March 1st from your account dashboard. The change was confirmed via email to your registered address. Would you like me to revert this change and process a prorated refund?',
    createdAt: new Date(Date.now() - 420000).toISOString(),
    toolCalls: [
      { id: 't2', toolName: 'get_activity_log', status: 'completed' as const, arguments: {} },
    ],
  },
  {
    id: '5',
    role: 'user' as const,
    content: 'Yes, please revert it and process the refund.',
    createdAt: new Date(Date.now() - 360000).toISOString(),
  },
  {
    id: '6',
    role: 'assistant' as const,
    content:
      'I\'ve initiated the plan reversion and refund request. The refund of $24.50 will be processed within 3-5 business days. You should receive a confirmation email shortly. Is there anything else I can help you with?',
    createdAt: new Date(Date.now() - 300000).toISOString(),
    toolCalls: [
      { id: 't3', toolName: 'process_refund', status: 'completed' as const, arguments: {} },
      { id: 't4', toolName: 'revert_plan', status: 'completed' as const, arguments: {} },
    ],
  },
];

export default function ConversationDetailPage() {
  const { id } = useParams();
  const [message, setMessage] = useState('');
  const [_isSending, setIsSending] = useState(false);

  const handleSend = () => {
    if (!message.trim()) return;
    setIsSending(true);
    // In a real app, this would call the API
    setTimeout(() => {
      setMessage('');
      setIsSending(false);
    }, 500);
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-6">
      {/* Chat area */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-surface-200 bg-white">
        {/* Chat header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <Link
              to="/conversations"
              className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-50 hover:text-surface-600"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h2 className="text-sm font-semibold text-surface-800">
                Billing inquiry about subscription #{id}
              </h2>
              <div className="flex items-center gap-2 text-xs text-surface-500">
                <Badge variant="info" dot size="sm">
                  active
                </Badge>
                <span>Alice Johnson</span>
                <span>&middot;</span>
                <span>Support Bot</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Phone className="h-3.5 w-3.5" />}
            >
              Escalate
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<CheckCircle className="h-3.5 w-3.5" />}
            >
              Resolve
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {mockMessages.map((msg) => (
            <div
              key={msg.id}
              className={clsx(
                'flex gap-3',
                msg.role === 'user' ? 'justify-end' : 'justify-start',
              )}
            >
              {msg.role === 'assistant' && (
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 shrink-0">
                  <Bot className="h-4 w-4 text-brand-600" />
                </div>
              )}
              <div
                className={clsx(
                  'max-w-[70%] rounded-2xl px-4 py-2.5',
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-surface-100 text-surface-800',
                )}
              >
                <p className="text-sm leading-relaxed">{msg.content}</p>
                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {msg.toolCalls.map((tc) => (
                      <div
                        key={tc.id}
                        className={clsx(
                          'flex items-center gap-1.5 rounded px-2 py-1 text-xs',
                          (msg.role as string) === 'user'
                            ? 'bg-white/10 text-white/80'
                            : 'bg-white text-surface-500',
                        )}
                      >
                        <CheckCircle className="h-3 w-3 text-success-500" />
                        {tc.toolName}
                      </div>
                    ))}
                  </div>
                )}
                <p
                  className={clsx(
                    'mt-1 text-xs',
                    msg.role === 'user' ? 'text-white/60' : 'text-surface-400',
                  )}
                >
                  {formatRelativeTime(msg.createdAt)}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-200 shrink-0">
                  <User className="h-4 w-4 text-surface-600" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input area */}
        <div className="border-t border-surface-200 p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type a message..."
              className="flex-1 rounded-lg border border-surface-200 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <Button onClick={handleSend} leftIcon={<Send className="h-4 w-4" />}>
              Send
            </Button>
          </div>
        </div>
      </div>

      {/* Sidebar info */}
      <div className="hidden w-80 shrink-0 space-y-4 xl:block">
        <Card padding="md">
          <h3 className="text-sm font-semibold text-surface-800 mb-3">Customer Info</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Avatar name="Alice Johnson" size="md" />
              <div>
                <p className="text-sm font-medium text-surface-800">Alice Johnson</p>
                <p className="text-xs text-surface-500">alice@example.com</p>
              </div>
            </div>
            <div className="border-t border-surface-100 pt-3 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-surface-500">Channel</span>
                <span className="font-medium text-surface-700">Web Widget</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-500">Agent</span>
                <span className="font-medium text-surface-700">Support Bot</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-surface-500">Sentiment</span>
                <Badge variant="warning" size="sm">neutral</Badge>
              </div>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <h3 className="text-sm font-semibold text-surface-800 mb-3">Timeline</h3>
          <div className="space-y-3">
            {[
              { icon: MessageSquare, text: 'Conversation started', time: '15m ago', color: 'text-brand-500' },
              { icon: AlertTriangle, text: 'Refund action pending', time: '5m ago', color: 'text-warning-500' },
              { icon: CheckCircle, text: 'Refund processed', time: '3m ago', color: 'text-success-500' },
            ].map((event, i) => (
              <div key={i} className="flex items-start gap-3">
                <event.icon className={clsx('h-4 w-4 mt-0.5 shrink-0', event.color)} />
                <div>
                  <p className="text-sm text-surface-700">{event.text}</p>
                  <p className="text-xs text-surface-400 flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {event.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card padding="md">
          <h3 className="text-sm font-semibold text-surface-800 mb-3">Tags</h3>
          <div className="flex flex-wrap gap-1.5">
            {['billing', 'subscription', 'refund'].map((tag) => (
              <Badge key={tag} variant="outline" size="sm">
                <Tag className="h-3 w-3" /> {tag}
              </Badge>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

const MessageSquare = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);
