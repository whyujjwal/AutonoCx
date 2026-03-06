import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';

interface Parameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
}

export default function ToolConfigPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  const [form, setForm] = useState({
    name: isNew ? '' : 'process_refund',
    description: isNew ? '' : 'Process a refund for a customer order',
    type: isNew ? '' : 'api',
    endpoint: isNew ? '' : 'https://api.internal.com/refunds',
    method: isNew ? 'POST' : 'POST',
    requiresApproval: !isNew,
    riskLevel: isNew ? 'low' : 'high',
  });

  const [parameters, setParameters] = useState<Parameter[]>(
    isNew
      ? []
      : [
          { name: 'order_id', type: 'string', description: 'The order ID to refund', required: true },
          { name: 'amount', type: 'number', description: 'Refund amount in cents', required: true },
          { name: 'reason', type: 'string', description: 'Reason for the refund', required: false },
        ],
  );

  const updateField = (field: string, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const addParameter = () => {
    setParameters([...parameters, { name: '', type: 'string', description: '', required: false }]);
  };

  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const updateParameter = (index: number, field: keyof Parameter, value: string | boolean) => {
    setParameters(
      parameters.map((p, i) => (i === index ? { ...p, [field]: value } : p)),
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tools')} className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">{isNew ? 'Add Tool' : 'Edit Tool'}</h1>
            <p className="mt-1 text-surface-500">{isNew ? 'Register a new tool' : `Editing ${form.name}`}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/tools')}>Cancel</Button>
          <Button leftIcon={<Save className="h-4 w-4" />}>{isNew ? 'Create' : 'Save'}</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card padding="md">
            <CardHeader><CardTitle>Basic Information</CardTitle></CardHeader>
            <div className="space-y-4">
              <Input label="Tool Name" value={form.name} onChange={(e) => updateField('name', e.target.value)} placeholder="e.g., process_refund" />
              <Input label="Description" value={form.description} onChange={(e) => updateField('description', e.target.value)} placeholder="What does this tool do?" />
              <div className="grid grid-cols-2 gap-4">
                <Select label="Type" value={form.type} onChange={(e) => updateField('type', e.target.value)} options={[{ value: 'api', label: 'API' }, { value: 'function', label: 'Function' }, { value: 'webhook', label: 'Webhook' }]} placeholder="Select type" />
                <Select label="Risk Level" value={form.riskLevel} onChange={(e) => updateField('riskLevel', e.target.value)} options={[{ value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }]} />
              </div>
            </div>
          </Card>

          {form.type === 'api' && (
            <Card padding="md">
              <CardHeader><CardTitle>API Configuration</CardTitle></CardHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <Select label="Method" value={form.method} onChange={(e) => updateField('method', e.target.value)} options={[{ value: 'GET', label: 'GET' }, { value: 'POST', label: 'POST' }, { value: 'PUT', label: 'PUT' }, { value: 'PATCH', label: 'PATCH' }, { value: 'DELETE', label: 'DELETE' }]} />
                  <div className="col-span-3">
                    <Input label="Endpoint URL" value={form.endpoint} onChange={(e) => updateField('endpoint', e.target.value)} placeholder="https://api.example.com/endpoint" />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-surface-700">Headers (JSON)</label>
                  <textarea rows={3} defaultValue='{"Authorization": "Bearer {{API_KEY}}"}' className="w-full rounded-lg border border-surface-300 px-3 py-2 font-mono text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20" />
                </div>
              </div>
            </Card>
          )}

          <Card padding="md">
            <CardHeader>
              <CardTitle>Parameters</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {parameters.map((param, index) => (
                <div key={index} className="flex items-start gap-3 rounded-lg border border-surface-200 p-3">
                  <div className="grid flex-1 grid-cols-2 gap-3">
                    <Input placeholder="Name" value={param.name} onChange={(e) => updateParameter(index, 'name', e.target.value)} />
                    <Select value={param.type} onChange={(e) => updateParameter(index, 'type', e.target.value)} options={[{ value: 'string', label: 'String' }, { value: 'number', label: 'Number' }, { value: 'boolean', label: 'Boolean' }, { value: 'object', label: 'Object' }]} />
                    <div className="col-span-2">
                      <Input placeholder="Description" value={param.description} onChange={(e) => updateParameter(index, 'description', e.target.value)} />
                    </div>
                    <label className="flex items-center gap-2 col-span-2">
                      <input type="checkbox" checked={param.required} onChange={(e) => updateParameter(index, 'required', e.target.checked)} className="h-4 w-4 rounded border-surface-300 text-brand-600" />
                      <span className="text-sm text-surface-600">Required</span>
                    </label>
                  </div>
                  <button onClick={() => removeParameter(index)} className="mt-1 rounded p-1 text-surface-400 hover:text-danger-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <Button variant="outline" className="w-full" leftIcon={<Plus className="h-4 w-4" />} onClick={addParameter}>
                Add Parameter
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card padding="md">
            <CardHeader><CardTitle>Settings</CardTitle></CardHeader>
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm text-surface-700">Requires Approval</span>
                <input type="checkbox" checked={form.requiresApproval} onChange={(e) => updateField('requiresApproval', e.target.checked)} className="h-4 w-4 rounded border-surface-300 text-brand-600" />
              </label>
              <p className="text-xs text-surface-500">
                When enabled, actions using this tool will require human approval before execution.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
