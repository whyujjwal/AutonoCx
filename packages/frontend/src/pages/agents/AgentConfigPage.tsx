import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Play, Bot } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export default function AgentConfigPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  const [form, setForm] = useState({
    name: isNew ? '' : 'Support Bot',
    description: isNew ? '' : 'General customer support agent',
    model: isNew ? '' : 'gpt-4o',
    provider: isNew ? '' : 'openai',
    systemPrompt: isNew
      ? ''
      : 'You are a helpful customer support agent for AutonoCX. Be polite, professional, and solution-oriented. Always verify customer identity before making account changes.',
    temperature: 0.7,
    maxTokens: 4096,
  });

  const [selectedTools, setSelectedTools] = useState<string[]>(
    isNew ? [] : ['lookup_account', 'process_refund', 'send_email'],
  );
  const [selectedKBs, setSelectedKBs] = useState<string[]>(
    isNew ? [] : ['product-docs'],
  );

  const [testMessage, setTestMessage] = useState('');
  const [testResponse, setTestResponse] = useState('');

  const updateField = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const availableTools = [
    'lookup_account',
    'process_refund',
    'send_email',
    'reset_password',
    'create_ticket',
    'search_docs',
    'update_plan',
    'verify_identity',
  ];

  const availableKBs = [
    { id: 'product-docs', name: 'Product Documentation' },
    { id: 'faq', name: 'FAQ Database' },
    { id: 'policies', name: 'Company Policies' },
  ];

  const handleTest = () => {
    if (!testMessage.trim()) return;
    setTestResponse(
      'I understand your concern about the billing charge. Let me look into your account to get more details about the recent charges.',
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/agents')}
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">
              {isNew ? 'Create Agent' : 'Edit Agent'}
            </h1>
            <p className="mt-1 text-surface-500">
              {isNew ? 'Configure a new AI agent' : `Editing ${form.name}`}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/agents')}>
            Cancel
          </Button>
          <Button leftIcon={<Save className="h-4 w-4" />}>
            {isNew ? 'Create Agent' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              <Input
                label="Agent Name"
                placeholder="e.g., Support Bot"
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
              />
              <Input
                label="Description"
                placeholder="Describe what this agent does"
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
              />
              <div className="grid grid-cols-2 gap-4">
                <Select
                  label="Provider"
                  value={form.provider}
                  onChange={(e) => updateField('provider', e.target.value)}
                  options={[
                    { value: 'openai', label: 'OpenAI' },
                    { value: 'anthropic', label: 'Anthropic' },
                    { value: 'google', label: 'Google' },
                  ]}
                  placeholder="Select provider"
                />
                <Select
                  label="Model"
                  value={form.model}
                  onChange={(e) => updateField('model', e.target.value)}
                  options={[
                    { value: 'gpt-4o', label: 'GPT-4o' },
                    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                    { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
                    { value: 'claude-3-5-haiku', label: 'Claude 3.5 Haiku' },
                    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
                  ]}
                  placeholder="Select model"
                />
              </div>
            </div>
          </Card>

          {/* System Prompt */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>System Prompt</CardTitle>
            </CardHeader>
            <textarea
              value={form.systemPrompt}
              onChange={(e) => updateField('systemPrompt', e.target.value)}
              rows={8}
              placeholder="Enter the system prompt for this agent..."
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 font-mono text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <div className="mt-2 flex items-center justify-between text-xs text-surface-500">
              <span>{form.systemPrompt.length} characters</span>
              <span>Supports Markdown and template variables</span>
            </div>
          </Card>

          {/* Model Parameters */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Model Parameters</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700">
                  Temperature: {form.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={form.temperature}
                  onChange={(e) => updateField('temperature', parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-surface-400">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
              <Input
                label="Max Tokens"
                type="number"
                value={form.maxTokens.toString()}
                onChange={(e) => updateField('maxTokens', parseInt(e.target.value))}
              />
            </div>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Tools */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Tools</CardTitle>
            </CardHeader>
            <div className="space-y-2">
              {availableTools.map((tool) => (
                <label key={tool} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTools.includes(tool)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedTools([...selectedTools, tool]);
                      } else {
                        setSelectedTools(selectedTools.filter((t) => t !== tool));
                      }
                    }}
                    className="h-4 w-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm text-surface-700">{tool}</span>
                </label>
              ))}
            </div>
          </Card>

          {/* Knowledge Bases */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Knowledge Bases</CardTitle>
            </CardHeader>
            <div className="space-y-2">
              {availableKBs.map((kb) => (
                <label key={kb.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedKBs.includes(kb.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedKBs([...selectedKBs, kb.id]);
                      } else {
                        setSelectedKBs(selectedKBs.filter((k) => k !== kb.id));
                      }
                    }}
                    className="h-4 w-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm text-surface-700">{kb.name}</span>
                </label>
              ))}
            </div>
          </Card>

          {/* Test Agent */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>Test Agent</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              <textarea
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                rows={3}
                placeholder="Type a test message..."
                className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                leftIcon={<Play className="h-3.5 w-3.5" />}
                onClick={handleTest}
              >
                Run Test
              </Button>
              {testResponse && (
                <div className="rounded-lg bg-surface-50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="h-4 w-4 text-brand-600" />
                    <span className="text-xs font-medium text-surface-600">Response</span>
                    <Badge variant="outline" size="sm">245 tokens</Badge>
                  </div>
                  <p className="text-sm text-surface-700">{testResponse}</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
