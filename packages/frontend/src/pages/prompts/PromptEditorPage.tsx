import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, History, Send } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDateTime } from '@/lib/formatters';

const mockVersions = [
  { id: 'v5', version: 5, changeNote: 'Added tone variable support', isPublished: true, createdBy: 'John Admin', createdAt: '2024-03-01T10:00:00Z' },
  { id: 'v4', version: 4, changeNote: 'Improved refund handling instructions', isPublished: false, createdBy: 'Jane Admin', createdAt: '2024-02-28T14:00:00Z' },
  { id: 'v3', version: 3, changeNote: 'Added escalation guidelines', isPublished: false, createdBy: 'John Admin', createdAt: '2024-02-20T09:00:00Z' },
];

export default function PromptEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  const [name, setName] = useState(isNew ? '' : 'Customer Support System Prompt');
  const [description, setDescription] = useState(isNew ? '' : 'Main system prompt for customer support agents');
  const [category, setCategory] = useState(isNew ? '' : 'system');
  const [content, setContent] = useState(
    isNew
      ? ''
      : `You are a helpful customer support agent for {{company_name}}. Your name is {{agent_name}}.

## Guidelines
- Be polite, professional, and solution-oriented
- Always verify customer identity before making account changes
- Use the tone: {{tone}}
- If unsure, escalate to a human agent rather than guessing

## Available Tools
You have access to the following tools to help customers:
- lookup_account: Look up customer details
- process_refund: Process refunds (requires approval for amounts > $100)
- send_email: Send emails to customers
- create_ticket: Create support tickets`,
  );
  const [changeNote, setChangeNote] = useState('');
  const [showVersions, setShowVersions] = useState(false);

  const detectedVariables = content.match(/\{\{(\w+)\}\}/g)?.map((v) => v.replace(/\{\{|\}\}/g, '')) ?? [];
  const uniqueVariables = [...new Set(detectedVariables)];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/prompts')} className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">{isNew ? 'Create Prompt' : 'Edit Prompt'}</h1>
            <p className="mt-1 text-surface-500">{isNew ? 'Create a new prompt template' : `Editing ${name}`}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {!isNew && (
            <Button variant="outline" leftIcon={<History className="h-4 w-4" />} onClick={() => setShowVersions(!showVersions)}>
              Versions
            </Button>
          )}
          <Button variant="outline" onClick={() => navigate('/prompts')}>Cancel</Button>
          <Button leftIcon={<Save className="h-4 w-4" />}>{isNew ? 'Create' : 'Save Version'}</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card padding="md">
            <CardHeader><CardTitle>Details</CardTitle></CardHeader>
            <div className="space-y-4">
              <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Prompt template name" />
              <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What is this prompt used for?" />
              <Select
                label="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                options={[
                  { value: 'system', label: 'System Prompt' },
                  { value: 'decision', label: 'Decision' },
                  { value: 'template', label: 'Template' },
                  { value: 'rag', label: 'RAG' },
                ]}
                placeholder="Select category"
              />
            </div>
          </Card>

          <Card padding="md">
            <CardHeader><CardTitle>Prompt Content</CardTitle></CardHeader>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={16}
              placeholder="Enter your prompt template... Use {{variable_name}} for template variables."
              className="w-full rounded-lg border border-surface-300 bg-white px-4 py-3 font-mono text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <div className="mt-2 flex items-center justify-between text-xs text-surface-500">
              <span>{content.length} characters</span>
              <span>{uniqueVariables.length} variables detected</span>
            </div>
          </Card>

          {!isNew && (
            <Card padding="md">
              <CardHeader><CardTitle>Version Note</CardTitle></CardHeader>
              <Input
                value={changeNote}
                onChange={(e) => setChangeNote(e.target.value)}
                placeholder="Describe what changed in this version..."
              />
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card padding="md">
            <CardHeader><CardTitle>Variables</CardTitle></CardHeader>
            {uniqueVariables.length === 0 ? (
              <p className="text-sm text-surface-500">No variables detected. Use {'{{variable_name}}'} syntax.</p>
            ) : (
              <div className="space-y-2">
                {uniqueVariables.map((v) => (
                  <div key={v} className="flex items-center gap-2 rounded-lg bg-surface-50 px-3 py-2">
                    <Badge variant="outline" size="sm">{`{{${v}}}`}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {!isNew && (
            <Card padding="md">
              <CardHeader><CardTitle>Test Prompt</CardTitle></CardHeader>
              <div className="space-y-3">
                {uniqueVariables.map((v) => (
                  <Input key={v} label={v} placeholder={`Value for ${v}`} />
                ))}
                <Button variant="outline" className="w-full" leftIcon={<Send className="h-3.5 w-3.5" />}>
                  Test with Values
                </Button>
              </div>
            </Card>
          )}

          {showVersions && (
            <Card padding="md">
              <CardHeader><CardTitle>Version History</CardTitle></CardHeader>
              <div className="space-y-3">
                {mockVersions.map((v) => (
                  <div key={v.id} className="flex items-start justify-between rounded-lg border border-surface-200 p-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-surface-800">v{v.version}</span>
                        {v.isPublished && <Badge variant="success" size="sm">published</Badge>}
                      </div>
                      <p className="mt-0.5 text-xs text-surface-500">{v.changeNote}</p>
                      <p className="mt-1 text-xs text-surface-400">
                        {v.createdBy} &middot; {formatDateTime(v.createdAt)}
                      </p>
                    </div>
                    {!v.isPublished && (
                      <Button variant="ghost" size="sm">Publish</Button>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
